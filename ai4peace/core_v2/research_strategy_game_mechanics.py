"""ResearchStrategy gamemaster implementation with modular game dynamics."""

import random
from json import JSONDecodeError
from typing import TYPE_CHECKING
import attrs

from ai4peace.core_v2 import ResearchStrategyPlayerStateUpdates
from ai4peace.core_v2.research_strategy_actions import ActionType, EspionageAction, MessageAction, Action, FundraiseAction, CreateResearchProjectAction, \
    CancelResearchProjectAction, InvestCapitalAction, SellCapitalAction, PoachTalentAction, LobbyAction, MarketingAction, AssetBalance, Message, ResearchProject

if TYPE_CHECKING:
    from typing import Any

import json
import re
import asyncio
import logging
from typing import Optional, Any, Dict, List
import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseTextChatMessage

from ai4peace.core_v2.new_architecture_draft import Player, GamemasterUpdateMessage, GenericGameMaster
from ai4peace.core_v2.new_architecture_draft import MoveCorrectionMessage, GameState, PlayerState

import pandas as pd

logger = logging.getLogger(__name__)

from ai4peace.core.utils import get_transcript_logger
script_logger = get_transcript_logger()


PLANNING_INDEX_TIMEDELTA = pd.DateOffset(months=3)
DATE_FORMAT = "%Y-%m-%d"

def get_budget_index(current_date: datetime.datetime, index_offset: pd.DateOffset=PLANNING_INDEX_TIMEDELTA, duration_years=10) -> list[str]:
    """Get a list of string budget indices (e.g. 2023-01-01, 2023-04-01, etc) for the given current date and index timedelta."""
    dates = pd.date_range(start=current_date, end=current_date + pd.Timedelta(years=duration_years), freq=index_offset)
    return [date.strftime(DATE_FORMAT) for date in dates]


@attrs.define
class PublicView:
    """Public view of a character's information."""
    asset_balance: AssetBalance
    stated_objectives: str
    stated_strategy: str
    public_artifacts: List[str] = attrs.field(factory=list)

@attrs.define
class PrivateInfo:
    """Private information for a character."""
    true_asset_balance: AssetBalance
    objectives: str
    strategy: str
    budget: Dict[str, float]  # budget by year
    espionage: List[Dict] = attrs.field(factory=list)
    projects: List[ResearchProject] = attrs.field(factory=list)
    

    def get_current_budget(self, current_date: datetime.datetime) -> float:
        """Get budget for the current year."""
        year = current_date.year
        return self.budget.get(str(year), 0.0)


@attrs.define
class ResearchStrategyPlayerState(PlayerState):
    """Player state for wargame simulation.
    This includes private information, public view, and game history.
    """
    name: str
    private_info: PrivateInfo
    public_view: PublicView
    inbox: List[Message] = attrs.field(factory=list)
    recent_actions: List[str] = attrs.field(factory=list)  # Last few rounds

    def add_message(self, message: Message):
        """Add a message to the inbox."""
        self.inbox.append(message)

    def get_messages_for_round(self, round_number: int) -> List[Message]:
        """Get messages for a specific round."""
        return [msg for msg in self.inbox if msg.round_number == round_number]


@attrs.define
class ResearchStrategyGameState(GameState):
    """Game state for wargame simulation.
    This includes global game state not visible to individual players.
    """
    current_date: datetime.datetime
    round_number: int
    public_events: List[str] = attrs.field(factory=list)
    game_history: List[str] = attrs.field(factory=list)  # Game master summaries

    def increment_round(self):
        """Increment to the next round."""
        self.round_number += 1
        # Increment date by some time period (e.g., 3 months per round)
        self.current_date += datetime.timedelta(days=90)


@attrs.define
class ResearchStrategyGamemasterUpdateMessage(GamemasterUpdateMessage):
    """Gamemaster update message for wargame simulation."""
    last_action_timestamp: datetime.datetime
    next_action_timestamp: datetime.datetime
    state_updates: ResearchStrategyPlayerStateUpdates


# Concrete Action subclasses


# Global default mapping of action types to their classes
ACTION_TYPE_TO_CLASS: Dict[ActionType, type] = {
    ActionType.FUNDRAISE: FundraiseAction,
    ActionType.CREATE_RESEARCH_PROJECT: CreateResearchProjectAction,
    ActionType.CANCEL_RESEARCH_PROJECT: CancelResearchProjectAction,
    ActionType.INVEST_CAPITAL: InvestCapitalAction,
    ActionType.SELL_CAPITAL: SellCapitalAction,
    ActionType.ESPIONAGE: EspionageAction,
    ActionType.POACH_TALENT: PoachTalentAction,
    ActionType.LOBBY: LobbyAction,
    ActionType.MARKETING: MarketingAction,
    ActionType.MESSAGE: MessageAction,
}


class ResearchStrategyPlayer(Player):
    """Player for wargame simulation using LLM agents."""

    def __init__(
            self,
            name: str,
            attributes: ResearchStrategyPlayerState,
            llm_client: Any,
            system_message_template: Optional[str] = None,
            available_actions: list[str] = list(ActionType.__members__.keys()),
            game_context: Optional[str] = None,
    ):
        """Initialize a wargame player.

        Args:
            name: Name of the character
            attributes: Current state of the character
            llm_client: Autogen LLM client
            system_message_template: Optional custom system message template
            game_context: Optional game context for building prompts
        """
        self.name = name
        self.attributes = attributes
        self.llm_client = llm_client
        self.game_context = game_context or ""

        # Validate available actions: These should all come from the ActionType enum:
        for action in available_actions:
            if action not in ActionType.__members__:
                raise ValueError(f"Invalid action: {action}")
        self.available_actions = available_actions

        # Build system message
        self.system_message = self._build_system_message(system_message_template)

        # Clean project_name for autogen (no special chars)
        self.clean_name = re.sub(r"\W|^(?=\d)", "_", self.name)

        logging.getLogger("autogen_agentchat").setLevel(logging.ERROR)
        self.agent = AssistantAgent(
            name=self.clean_name,
            model_client=llm_client,
            system_message=self.system_message,
            tools=[],  # Can add tools here for RAG memory
        )

        # Action history for tracking
        self.action_history: Dict = {}

        self.max_attempts: int = 3  # Max attempts for LLM response parsing

    def _build_system_message(self, template: Optional[str] = None) -> str:
        """Build the system message for the agent."""
        if template:
            return template

        private = self.attributes.private_info
        public = self.attributes.public_view
        system_message = f"""You are {self.name}, a participant in an international technology policy simulation.

## Your Identity and Goals

{private.objectives}

## Your Strategy

{private.strategy}

## Format for Your Responses

You must respond with a JSON object containing a list of actions you want to take this round. Each entry of the list should follow one of the following formats:
- {{"type": "cancel_research_project", "project_name": "<str>"}}
- {{"type": "create_research_project", "project_name": "<str>", "description": "<str>", "target_completion_date": "<ISO date>", "annual_budget": <float>, "required_assets": {{"technical_capability": <float>, "capital": <float>, "human": <float>}}}}
Note: A more concrete, realistic, and well-scoped project is more likely to be approved. Allocate a _subset_ of your _current_ technical capability, capital, and human resources. Projects needing more resources than you currently have will not be approved.
- {{"type": "espionage", "target_player": "<character project_name>", "budget": <float>, "focus": "<what to investigate>"}}
- {{"type": "fundraise", "amount": <float>, "description": "<str>"}}
- {{"type": "invest_capital", "amount": <float>}}
- {{"type": "lobby", "message": "<str>", "budget": <float>}}
- {{"type": "marketing", "message": "<str>", "budget": <float>}}
- {{"type": "poach_talent", "target": "<character project_name>", "budget": <float>}}
- {{"type": "sell_capital", "amount": <float>}}
- {{"type": "bilateral_message", "to_character": "<character project_name>", "content": "<message text>"}}

Be sure that your budgets and timelines for all research/capital projects are reasonable. All actions will be validated before being executed.

Always respond with valid JSON only, no additional text."""

        return system_message
    
    def update_state(self, msg: ResearchStrategyGamemasterUpdateMessage) -> None:
        """Update player state based on gamemaster message."""
        updates = msg.state_updates

        # Update budget
        for year, delta in updates.budget_changes.items():
            current = self.attributes.private_info.budget.get(year, 0.0)
            self.attributes.private_info.budget[year] = current + delta

        # Update asset balance
        if updates.asset_balance_changes:
            self.attributes.private_info.true_asset_balance = (
                self.attributes.private_info.true_asset_balance.add(updates.asset_balance_changes)
            )

        # Update research projects
        for project in updates.new_projects:
            self.attributes.private_info.projects.append(project)

        for project in updates.updated_projects:
            # Find and update existing project
            for i, p in enumerate(self.attributes.private_info.projects):
                if p.project_name == project.project_name:
                    self.attributes.private_info.projects[i] = project
                    break

        for project_name in updates.completed_projects:
            for project in self.attributes.private_info.projects:
                if project.project_name == project_name:
                    project.status = "completed"
                    break

        for project_name in updates.cancelled_projects:
            for project in self.attributes.private_info.projects:
                if project.project_name == project_name:
                    project.status = "cancelled"
                    break

        # Add messages
        for message in updates.new_messages:
            self.attributes.add_message(message)

        # Update public views of other players
        self.attributes.public_view = updates.other_players_public_views.get(
            self.name, self.attributes.public_view
        )

        # Store action results
        if updates.action_results:
            for result in updates.action_results:
                self.attributes.recent_actions.extend(result)
            # NOTE: this was keeping last 5, I increased to last 20
            self.attributes.recent_actions = self.attributes.recent_actions[-20:]

        # Store in action history
        self.action_history[str(msg.last_action_timestamp)] = {
            "budget_changes": updates.budget_changes,
            "asset_balance_changes": updates.asset_balance_changes.to_dict() if updates.asset_balance_changes else None,
            "action_results": updates.action_results,
            "public_events": updates.public_events,
            "espionage_results": updates.espionage_results,
        }

    async def propose_actions(
            self,
            game_state_summary: str,
            private_updates: str,
            current_date: datetime.datetime,
            round_number: int,
            other_player_names: str
    ) -> List[Action]:
        """Propose actions with full game context."""
        prompt = self._build_prompt(
            game_state_summary, private_updates, current_date, round_number, other_player_names
        )

        # NOTE: this is where we send the LLM the raw prompt
        response = await self._get_llm_response(prompt)
        # from ai4peace.core_v2.test_tools import response_text_1
        # response = response_text_1

        # Parse response into actions
        moves = self._parse_response(response, round_number)
        if not moves:
            # we've failed to parse any actions!
            logger.warning("No moves received")
        return moves

    def _build_prompt(
            self,
            game_state_summary: str,
            private_updates: str,
            current_date: datetime.datetime,
            round_number: int,
            other_player_names: list
    ) -> str:
        """Build the prompt for a specific round."""
        # TODO: this has the full prompt we send to the LLM to extract actions — this is where
        # we would iterate on prompt templates
        # Get recent actions
        recent_actions = "\n".join(self.attributes.recent_actions) # [-5:])

        # Get messages for this round
        current_messages = self.attributes.get_messages_for_round(round_number)
        message_text = ""
        if current_messages:
            message_text = "\n\n## Private Messages Received:\n"
            for msg in current_messages:
                message_text += f"\nFrom {msg.from_character}: {msg.content}\n"

        prompt = f"""## Game Context

{self.game_context}

## Current Game Date
{current_date.strftime('%Y-%m-%d')}

## Round {round_number}

### Global Game State Summary
{game_state_summary}

### Your Recent Actions
{recent_actions if recent_actions else "None yet"}
{message_text}

### Your Private Updates
{private_updates}

### Your Current Resources
- Budget: ${self.attributes.private_info.get_current_budget(current_date):,.0f}
- Assets:
  * Technical Capability: {self.attributes.private_info.true_asset_balance.technical_capability:.2f}
  * Capital: {self.attributes.private_info.true_asset_balance.capital:.2f}
  * Human Resources: {self.attributes.private_info.true_asset_balance.human:.2f}

### Active Research Projects
{self._format_projects()}

## Available Actions

You can take multiple actions per round. Consider these options carefully.
Note that these are ordered alphabetically and not by likely usefulness or priority.

1. **Cancel Projects** - Free up resources by cancelling research
2. **Capital Investment** - Invest in infrastructure, factories, compute, etc.
3. **Create Research Projects** - Create new research initiatives by allocating a _subset_ of your _current_ technical capability, capital, and human resources. 
    Projects needing more resources than you currently have will not be approved.
4. **Fundraising** - Request budget increases or raise capital
5. **Lobbying** - Influence public opinion and policy (may backfire)
6. **Marketing** - Promote your position publicly
7. **Poach Talent** - Attempt to recruit from one of the other organizations (use the organization's name as the 'target', i.e. one of: {other_player_names})
8. **Private Messages** - Negotiate with other characters directly
9. **Research Projects** - Create new research initiatives (will consume budget and assets)
10. **Sell Capital** - Divest assets to raise funds

What actions do you want to take this round? Respond with a JSON object as specified in your system message."""

        return prompt

    def _format_projects(self) -> str:
        """Format current research projects."""
        if not self.attributes.private_info.projects:
            return "None"

        lines = []
        for project in self.attributes.private_info.projects:
            if project.status == "active":
                lines.append(
                    f"- {project.project_name}: {project.progress * 100:.0f}% complete, "
                    f"target: {project.target_completion_date.strftime('%Y-%m-%d')}"
                )
        return "\n".join(lines) if lines else "None"

    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM via Autogen."""
        try:
            messages = [
                BaseTextChatMessage(source=self.clean_name, content=self.system_message),
                BaseTextChatMessage(source=self.clean_name, content=prompt)
            ]

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name} - System message length: {len(self.system_message)} chars")
                logger.debug(f"{self.name} - Prompt length: {len(prompt)} chars")

            response = await self.agent.run(task=messages)
            response_content = response.messages[-1].content if response.messages else ""

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name} - Response length: {len(response_content)} chars")
                logger.debug(f"{self.name} - Full response:\n{response_content}")

            return response_content

        except Exception as e:
            logger.error(f"{self.name} - LLM call failed: {e}", exc_info=True)
            return json.dumps({"actions":[]})

    def _get_llm_response_blocking(self, prompt: str) -> str:
        coro = self._get_llm_response(prompt)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop running in this thread -> safe to run synchronously
            return asyncio.run(coro)
        else:
            # Already in an event loop -> you MUST await instead of blocking
            raise RuntimeError(
                "_get_llm_response_blocking() called while an event loop is running. Make the caller async and `await _get_llm_response(...)`."
            )

    @staticmethod
    def extract_json_from_response(response_text: str) -> Dict:
        try:
            return json.loads(response_text)
        except JSONDecodeError:
            # This block handles cases where the LLM wraps the JSON in a code block or other formatting.
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError:
                    logger.error(f"Could not parse response as JSON: {response_text}")
                    return []
            else:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Could not parse extracted JSON: {json_match.group()}")
                    return []
            return data

    def _parse_response(self, response_text: str, round_number:int = None) -> List[Action]:
        """Parse agent/LLM response into Action."""
        # Try to extract JSON from response
        logger.debug(f"raw LLM response: {response_text}")

        data = self.extract_json_from_response(response_text)
        if isinstance(data, dict):
            if "actions" in data:
                actions_data = data['actions']
            elif 'type' in data:
                actions_data = [data]
            else:
                logger.error(f"Unexpected data format in dict: {data}")
                return []
        elif isinstance(data, list):
            assert all(isinstance(item, dict) and 'type' in item for item in data), "All items in the list must be action dictionaries"
            actions_data = data
        else:
            logger.error(f"Unexpected data format: {data}")
            return []

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self.name} - Parsing {len(actions_data)} actions")

        script_logger.info({"round" : round_number, "log_type" : "raw_llm_actions_messages",
                    "player" : self.name, "llm_response" : data})

        # Create moves from actions
        moves = []
        for action_dict in actions_data:
            move = self._create_move_from_dict(action_dict)
            if move is not None:  # Only add if valid action
                moves.append(move)

        return moves

    def _create_move_from_dict(
            self, action_dict: Dict
    ) -> Action | None:
        """Create a Action from a dictionary.
        
        Uses the action_type_to_class mapping to dynamically instantiate the
        appropriate Action subclass from the dictionary using attrs.
        """
        action_type_string = action_dict.pop("type", None)
        if not action_type_string or action_type_string not in ActionType:
            logger.warning(f"Unknown action type: {action_dict.get('type')}")
            # TODO: Do we want corrective handling of errors which occur while creating the Action?
            return

        action_type = ActionType(action_type_string)
        action_class = ACTION_TYPE_TO_CLASS[action_type]

        # Prepare the data dictionary for instantiation
        action_data = {"initiating_character_name": self.name}
        action_data.update(action_dict)

        try:
            action = action_class(**action_data)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to instantiate {action_class.__name__} from dict: {e}")
            return None
        return action

    async def correct_moves(
            self, move_modifications: MoveCorrectionMessage, round_number:int=None
    ) -> Action:
        """Correct moves based on gamemaster feedback."""
        logger.info(f"{self.name} - Proposed action failed: {move_modifications.error_message}")
        original_move_obj = attrs.asdict(move_modifications.original_move)
        original_move_obj.pop('initiating_character_name')
        original_move_obj['type'] = move_modifications.original_move.action_type.value

        updated_moves = []
        for i in range(self.max_attempts):
            correction_msg = f"""
Your proposed move described below was rejected, due to the following reason: {move_modifications.error_message}. Please update this specific proposed action to correct the issue. Do not include other actions; just provide one action in your response.
You currently have the following limited resources, and must spend them wisely: {attrs.asdict(self.attributes.private_info.true_asset_balance)}\n
PREVIOUS PROPOSAL:\n
{json.dumps(original_move_obj)}"""
            response = await self._get_llm_response(correction_msg)

            updated_moves = self._parse_response(response)
            if updated_moves:
                return updated_moves[0]
        script_logger.info({"round" : round_number,"log_type" : "gm_action_correction",
                            "player" : self.name, "status" : "fail",
                            "original_move" : move_modifications.original_move.to_dict(),
                            "correction" :  move_modifications.error_message})

        return move_modifications.original_move  # Fallback to original move if correction fails


@attrs.define
class ResearchStrategyGameMaster(GenericGameMaster):
    """Game master for wargame simulation with modular game dynamics."""
    
    players: List[ResearchStrategyPlayer] = attrs.field(factory=list)
    current_time: datetime.datetime = attrs.field(factory=datetime.datetime.now)
    default_timestep: datetime.timedelta = attrs.field(factory=lambda: datetime.timedelta(days=90))
    current_gamemaster_updates: Dict[str, ResearchStrategyGamemasterUpdateMessage] = attrs.field(factory=dict)
    game_state: ResearchStrategyGameState = attrs.field(factory=lambda: ResearchStrategyGameState(
        current_date=datetime.datetime.now(),
        round_number=0,
    ))
    round_number: int = 0
    random_seed: Optional[int] = None
    random_events: List[str] = attrs.field(factory=list)
    fixed_events: Dict[int, str] = {}

    # Action type to class mapping
    action_type_to_class: Dict[ActionType, type] = attrs.field(default=ACTION_TYPE_TO_CLASS)
    
    # Game dynamics parameters (non-action-specific)
    research_progress_rate_base: float = 0.1
    research_progress_rate_max: float = 0.3
    research_human_scaling: float = 100.0  # Human resources per unit of progress rate
    information_leak_probability: float = 0.05
    random_event_probability: float = 0.1

    max_attempts: int = 3  # Max attempts for move correction loops

    _random: random.Random = attrs.field(init=False)
    
    def __attrs_post_init__(self):
        self._random = random.Random(self.random_seed)
    
    def get_timestep(self):
        """Get the current timestep."""
        return self.default_timestep
    
    def create_player_update_messages(self, player: ResearchStrategyPlayer) -> ResearchStrategyGamemasterUpdateMessage:
        """Create update message for a player."""
        # Get public views of other players
        other_players_public_views = {}
        for other_player in self.players:
            if other_player.name != player.name:
                other_players_public_views[other_player.name] = other_player.attributes.public_view
        
        # Create empty state updates (will be filled during simulation)
        state_updates = ResearchStrategyPlayerStateUpdates(
            other_players_public_views=other_players_public_views,
            public_events=self.game_state.public_events[-5:],  # Last 5 events
        )
        
        return ResearchStrategyGamemasterUpdateMessage(
            last_action_timestamp=self.current_time,
            next_action_timestamp=self.current_time + self.get_timestep(),
            state_updates=state_updates
        )
    
    async def get_player_move(self, player: ResearchStrategyPlayer) -> List[Action]:
        """Get validated move from player, with correction loop."""
        
        # Build context for player
        game_state_summary = self._create_game_state_summary()
        private_updates = self._create_private_updates_summary(player, game_state=self.game_state)

        # get all player names
        other_player_names = [p.name for p in self.players if p.name != player.name]
        
        for attempt in range(self.max_attempts):
            moves_to_validate = await player.propose_actions(
                game_state_summary=game_state_summary,
                private_updates=private_updates,
                current_date=self.game_state.current_date,
                round_number=self.game_state.round_number,
                other_player_names=other_player_names
            )
            valid_moves = []
            current_move_index = 0
            while len(moves_to_validate) > 0 and current_move_index < len(moves_to_validate):
                candidate_move = moves_to_validate[current_move_index]

                validation_error = candidate_move.validate_action(game_state=self.game_state,
                                                        players=self.players,
                                                        gamemaster=self)
                if validation_error is None:
                    valid_move = moves_to_validate.pop(current_move_index)  # Because the list shrinks, don't need to update the index
                    valid_moves.append(valid_move)
                else:
                    correction = MoveCorrectionMessage(
                        original_move=candidate_move,
                        error_message=validation_error
                    )
                    logger.debug("Requesting correction: "+ validation_error)
                    updated_move = await player.correct_moves(correction)
                    moves_to_validate[current_move_index] = updated_move
                    current_move_index += 1
        return valid_moves

    def simulate_one_round(
        self, game_state: ResearchStrategyGameState, actions: Dict[str, List[Action]]
    ):
        """Simulate one round of the research strategy game.

        Actions are grouped by type and processed together, allowing for better
        modeling of competition for resources, resolution of uncertainty, etc.
        """
        # Step 1: Increment time
        game_state.increment_round()
        self.round_number = game_state.round_number
        
        # Step 2: Convert moves to Action instances and group by type
        actions_by_type: Dict[ActionType, List[Action]] = {}
        for player_name, move_list in actions.items():
            player = self._get_player_by_name(player_name)
            if not player:
                continue
            
            for action in move_list:
                action.initiating_character_name = player_name
                action_type = action.action_type
                if action_type not in actions_by_type:
                    actions_by_type[action_type] = []
                actions_by_type[action_type].append(action)
        
        # Step 3: Process actions by type (allowing for batch processing)
        # Initialize action results for all players
        action_results: Dict[str, List[str]] = {}
        for player in self.players:
            action_results[player.name] = []

        # Process each action type
        for action_type, actions_to_process in actions_by_type.items():
            if not actions_to_process:
                continue

            action_class = self.action_type_to_class.get(action_type)

            # Process all actions of this type together
            type_updates = action_class.handle_actions(
                actions_to_process, game_state, self.players, self
            )

            # Merge updates into action_results
            for player_name, updates in type_updates.items():
                if player_name not in action_results:
                    action_results[player_name] = []
                action_results[player_name].extend(updates.action_results)

        # Step 4: TODO: RETHINK THIS- should be able to trigger actions (like research evolution) which continue to evolve even without ongoing player actions
        self._update_research_projects(game_state)

        # Introduce random events & fixed events
        self._simulate_information_leaks(game_state)
        self._introduce_random_events(game_state)
        self._introduce_fixed_events(game_state)

        # Create update messages for all players
        self._create_update_messages(game_state, action_results)
        
        #  Update timestamps
        self.current_time = game_state.current_date
    
    def _process_messages(
        self, game_state: ResearchStrategyGameState, all_player_actions: Dict[str, List[Action]]
    ):
        """Process private messages between characters."""
        for player_name, actions in all_player_actions.items():
            for action in actions:
                if action.action_type == ActionType.MESSAGE:
                    target_player = self._get_player_by_name(action.to_character)
                    target_player.attributes.add_message(action)

    def _update_research_projects(self, game_state: ResearchStrategyGameState):
        """Update all active research projects."""
        for player in self.players:
            for project in player.attributes.private_info.projects:
                if project.status == "active":
                    # Simulate research progress
                    progress_rate = min(
                        self.research_progress_rate_base + (project.committed_assets.human / self.research_human_scaling),
                        self.research_progress_rate_max
                    )
                    project.progress = min(project.progress + progress_rate, 1.0)

                    # Check if completed
                    if project.progress >= 1.0:
                        project.status = "completed"

                    # Deduct budget
                    year = str(game_state.current_date.year)
                    budget = player.attributes.private_info.budget.get(year, 0.0)
                    if budget >= project.committed_budget:
                        player.attributes.private_info.budget[year] = budget - project.committed_budget
    
    def _simulate_information_leaks(self, game_state: ResearchStrategyGameState):
        """Simulate information leaks through reporter investigations."""
        if self._random.random() < self.information_leak_probability:
            # Select a random character
            character = self._random.choice(self.players)
            
            # Leak some information
            leak_info = (
                f"Leaked intelligence reports suggest {character.name} has "
                f"approximately ${character.attributes.private_info.budget.get(str(game_state.current_date.year), 0):,.0f} "
                f"in budget and {character.attributes.private_info.true_asset_balance.human:.1f} human resources."
            )
            
            game_state.public_events.append(leak_info)
    
    def _introduce_random_events(self, game_state: ResearchStrategyGameState):
        """Introduce random external events."""
        if self._random.random() < self.random_event_probability and self.random_events:
            event = self._random.choice(self.random_events)
            game_state.public_events.append(f"Round {game_state.round_number}: {event}")

    def _introduce_fixed_events(self, game_state: ResearchStrategyGameState):
        if self.fixed_events:
             for round, event in self.fixed_events.items():
                if game_state.round_number == int(round):
                    game_state.public_events.append(f"Round {game_state.round_number}: {event}")
    
    def _create_update_messages(
        self, game_state: ResearchStrategyGameState, action_results: List[Dict[str, List[str]]]
    ):
        """Create update messages for all players."""
        # Create global action summary
        action_summary = self._create_action_summary(game_state, action_results)
        logger.info(action_summary)
        summary_dict = self._create_action_summary_for_transcript(game_state, action_results)
        script_logger.info({"round" : game_state.round_number,"log_type" : "round_summary", "summary" : summary_dict})
        game_state.game_history.append(action_summary)
        
        # Create update messages for each player
        for player in self.players:
            updates = ResearchStrategyPlayerStateUpdates()
            
            # Add action results
            if player.name in action_results:
                # NOTE: this will be a list, so let's flatten it!
                updates.action_results = [action_result for result_list in action_results[player.name] for action_result in result_list]
            
            # Add espionage results
            if hasattr(player.attributes, '_private_updates'):
                updates.espionage_results = player.attributes._private_updates
                player.attributes._private_updates = []
            
            # Add research project updates
            for project in player.attributes.private_info.projects:
                if project.status == "completed":
                    updates.completed_projects.append(project.project_name)
                elif project.status == "active":
                    updates.updated_projects.append(project)
            
            # Add messages received this round
            updates.new_messages = player.attributes.get_messages_for_round(game_state.round_number)
            
            # Add public views of other players
            for other_player in self.players:
                if other_player.name != player.name:
                    updates.other_players_public_views[other_player.name] = other_player.attributes.public_view
            
            # Add public events
            updates.public_events = game_state.public_events[-5:]
            
            # Add global summary
            updates.global_summary = action_summary
            # Create update message
            update_msg = ResearchStrategyGamemasterUpdateMessage(
                last_action_timestamp=self.current_time,
                next_action_timestamp=self.current_time + self.get_timestep(),
                state_updates=updates
            )
            
            self.current_gamemaster_updates[player.name] = update_msg
    
    def _create_action_summary(
        self, game_state: ResearchStrategyGameState, action_results: Dict[str, List[str]]
    ) -> str:
        """Create a summary of all actions taken this round."""
        summary_parts = [f"Round {game_state.round_number} Summary ({game_state.current_date.strftime('%Y-%m-%d')}):"]
        logger.debug(f"raw results: {action_results}")
        for player_name, results in action_results.items():
            summary_parts.append(f"\n{player_name}:")
            for result in results:
                summary_parts.append(f"  - {result}")
        
        # Add public events
        if game_state.public_events:
            summary_parts.append("\nPublic Events:")
            # NOTE: removing constraint on "last five events" here for now
            for event in game_state.public_events:
                summary_parts.append(f"  - {event}")
        
        return "\n".join(summary_parts)
    
    def _create_action_summary_for_transcript(
            self, game_state: ResearchStrategyGameState, action_results: Dict[str, List[str]]
    ) -> Dict:
        """Create a jsonl summary of all actions taken this round."""
        summary = {"round" : game_state.round_number, 
                   "date" : game_state.current_date.strftime('%Y-%m-%d')}
      
        results_by_player = {}
        for player_name, results in action_results.items():
            results_by_player[player_name] = results
        summary["results"] = results_by_player

        # Add public events
        if game_state.public_events:
            summary["events"] = [f"{event}" for event in game_state.public_events]
        return summary
    
    def _create_game_state_summary(self) -> str:
        """Create summary of global game state."""
        if self.game_state.game_history:
            # NOTE: why such a short history?
            return self.game_state.game_history[-1]
        return "Game starting..."
    
    def _create_private_updates_summary(self, player: ResearchStrategyPlayer, game_state: ResearchStrategyGameState) -> str:
        """Create summary of private updates for a player."""
        updates = []
        
        # Add research project updates
        for project in player.attributes.private_info.projects:
            if project.status == "completed":
                updates.append(f"Research project '{project.project_name}' has been completed!")
            elif project.status == "active":
                updates.append(
                    f"Research project '{project.project_name}' is {project.progress * 100:.0f}% complete."
                )

        for esp_result in player.attributes.private_info.espionage:
            if  "success" in esp_result and esp_result["success"]:
                target_player = self._get_player_by_name(esp_result["target"])
                if target_player:
                    updates.append(
                        f"Espionage on {esp_result['target']} ({esp_result['focus']}): "
                        # TODO: how to properly pass this?
                        f"Discovered budget ≈${target_player.attributes.private_info.budget.get(str(game_state.current_date.year), 0):,.0f}, "
                        f"assets: tech={target_player.attributes.private_info.true_asset_balance.technical_capability:.1f}, "
                        f"capital={target_player.attributes.private_info.true_asset_balance.capital:.1f}, "
                        f"human={target_player.attributes.private_info.true_asset_balance.human:.1f}"
            )
        
        return "\n".join(updates) if updates else "No significant private updates."
    
    def _get_player_by_name(self, name: str) -> Optional[ResearchStrategyPlayer]:
        """Get player by project_name."""
        for player in self.players:
            if player.name == name:
                return player
        return None
    
    def get_game_ending(self) -> Optional[str]:
        """Check if game is over. Returns ending message if game is over, None otherwise."""
        # For now, games don't have explicit endings
        # Can be overridden by scenarios
        return None
    
    def log_game_state(self):
        """Log current game state."""
        logger.info(f"Round {self.game_state.round_number} ({self.game_state.current_date.strftime('%Y-%m-%d')})")
        for player in self.players:
            logger.info(
                f"{player.name}: Budget=${player.attributes.private_info.get_current_budget(self.game_state.current_date):,.0f}, "
                f"Tech={player.attributes.private_info.true_asset_balance.technical_capability:.1f}, "
                f"Capital={player.attributes.private_info.true_asset_balance.capital:,.0f}, "
                f"Human={player.attributes.private_info.true_asset_balance.human:.1f}"
            )
    def log_game_state_dict(self):
        """Log current game stats as a dictionary"""
        game_state_dict = {"round" : self.game_state.round_number, "time" : str(self.game_state.current_date.strftime('%Y-%m-%d'))}
        for player in self.players:
            game_state_dict[player.name] = {
                "budget" : player.attributes.private_info.get_current_budget(self.game_state.current_date),
                "tech_capability" : player.attributes.private_info.true_asset_balance.technical_capability,
                "capital" : player.attributes.private_info.true_asset_balance.capital,
                "num_humans" : player.attributes.private_info.true_asset_balance.human
        }
        script_logger.info({"round" : self.game_state.round_number, "log_type" : "game_state", "game_state" : game_state_dict})

    async def run_simulation(self):
        """Run the full simulation."""
        logger.info("Starting research strategy simulation")
        logger.info(f"Players: {[p.name for p in self.players]}")
        
        # Initial update messages for all players
        for player in self.players:
            update_msg = self.create_player_update_messages(player)
            player.update_state(update_msg)
            self.current_gamemaster_updates[player.name] = update_msg
        
        max_rounds = 3 
        round_count = 0
        
        self.log_game_state()
        self.log_game_state_dict()
        while round_count < max_rounds:
            round_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Round {round_count}")
            logger.info(f"{'='*60}")
            
            # Get a list of actions from each player
            actions = {}
            for player in self.players:
                per_player_actions = await self.get_player_move(player)
                actions[player.name] = per_player_actions
            # NOTE: we have the actions here, so we could log them here?

            # Simulate the round
            self.simulate_one_round(self.game_state, actions)
            
            # Update all players with the new state
            for player in self.players:
                if player.name in self.current_gamemaster_updates:
                    player.update_state(self.current_gamemaster_updates[player.name])
            
            # Log current state
            self.log_game_state()
            self.log_game_state_dict()

            # Check for game ending
            ending = self.get_game_ending()
            if ending:
                logger.info(f"\n{'='*60}")
                logger.info(f"Game Over: {ending}")
                logger.info(f"{'='*60}")
                break
        
        if round_count >= max_rounds:
            logger.warning(f"Game reached maximum rounds ({max_rounds})")
