"""ResearchStrategy gamemaster implementation with modular game dynamics."""

import random
from shutil import move
from .new_architecture_draft import PlayerStateUpdates, GamemasterUpdateMessage


from .new_architecture_draft import GenericGameMaster

from typing import Dict, List, Optional
from enum import Enum
import attrs


import json
import re
import asyncio
import logging
from typing import Optional, Any, Dict, List
import datetime
import pprint

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseTextChatMessage

from .new_architecture_draft import Player
from .new_architecture_draft import PlayerProposedMove, MoveCorrectionMessage

from ..core.utils import get_transcript_logger
import pandas as pd

logger = logging.getLogger(__name__)
script_logger = get_transcript_logger()

from .new_architecture_draft import GameState, PlayerState

PLANNING_INDEX_TIMEDELTA = pd.DateOffset(months=3)
DATE_FORMAT = "%Y-%m-%d"

def get_budget_index(current_date: datetime.datetime, index_offset: pd.DateOffset=PLANNING_INDEX_TIMEDELTA, duration_years=10) -> list[str]:
    """Get a list of string budget indices (e.g. 2023-01-01, 2023-04-01, etc) for the given current date and index timedelta."""
    dates = pd.date_range(start=current_date, end=current_date + pd.Timedelta(years=duration_years), freq=index_offset)
    return [date.strftime(DATE_FORMAT) for date in dates]

@attrs.define
class AssetBalance:
    """Represents a character's asset balance."""
    technical_capability: float = 0.0
    capital: float = 0.0 # Unallocated capital
    human: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "technical_capability": self.technical_capability,
            "capital": self.capital,
            "human": self.human,
        }

    def add(self, other: "AssetBalance") -> "AssetBalance":
        return AssetBalance(
            technical_capability=self.technical_capability + other.technical_capability,
            capital=self.capital + other.capital,
            human=self.human + other.human,
        )

    def subtract(self, other: "AssetBalance") -> "AssetBalance":
        return AssetBalance(
            technical_capability=self.technical_capability - other.technical_capability,
            capital=self.capital - other.capital,
            human=self.human - other.human,
        )


@attrs.define
class ResearchProject:
    """A research or capital investment project."""
    name: str
    description: str
    target_completion_date: datetime.datetime
    # original_budget: float # the budget the project was originally proposed for, for calculating overruns
    committed_budget: float  # per year
    committed_assets: AssetBalance
    status: str = "active"  # active, completed, cancelled
    progress: float = 0.0  # 0.0 to 1.0
    realistic_goals: Optional[str] = None  # Modified by gamemaster if unrealistic


@attrs.define
class Message:
    """A private message between characters."""
    from_character: str
    to_character: str
    content: str
    timestamp: datetime.datetime
    round_number: int


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
class ResearchStrategyPlayerStateUpdates(PlayerStateUpdates):
    """Player state updates for wargame simulation.
    This includes changes to the player's state, including:
    - Budget changes
    - Asset balance changes
    - Research project updates
    - Messages received
    - Public information about other players
    - Public events
    """
    # Budget and asset changes
    budget_changes: Dict[str, float] = attrs.field(factory=dict)  # year -> delta
    asset_balance_changes: Optional[AssetBalance] = None

    # Research project updates
    new_projects: List[ResearchProject] = attrs.field(factory=list)
    updated_projects: List[ResearchProject] = attrs.field(factory=list)
    completed_projects: List[str] = attrs.field(factory=list)  # project names
    cancelled_projects: List[str] = attrs.field(factory=list)  # project names

    # Messages received
    new_messages: List[Message] = attrs.field(factory=list)

    # Public information about other players
    other_players_public_views: Dict[str, PublicView] = attrs.field(factory=dict)

    # Public events
    public_events: List[str] = attrs.field(factory=list)

    # Action results
    action_results: List[str] = attrs.field(factory=list)  # Descriptions of what happened

    # Espionage results (private information discovered)
    espionage_results: List[str] = attrs.field(factory=list)

    # Global game state summary
    global_summary: str = ""


@attrs.define
class ResearchStrategyGamemasterUpdateMessage(GamemasterUpdateMessage):
    """Gamemaster update message for wargame simulation."""
    last_action_timestamp: datetime.datetime
    next_action_timestamp: datetime.datetime
    state_updates: ResearchStrategyPlayerStateUpdates



class ActionType(Enum):
    """Types of actions agents can take."""
    FUNDRAISE = "fundraise"
    CREATE_RESEARCH_PROJECT = "create_research_project"
    CANCEL_RESEARCH_PROJECT = "cancel_research_project"
    INVEST_CAPITAL = "invest_capital"
    SELL_CAPITAL = "sell_capital"
    ESPIONAGE = "espionage"
    POACH_TALENT = "poach_talent"
    LOBBY = "lobby"
    MARKETING = "marketing"
    MESSAGE = "message"  # Private message to another character


@attrs.define
class ResearchProjectAction:
    """Details for creating a research project."""
    name: str
    description: str
    target_completion_date: str  # ISO format date
    annual_budget: float
    required_assets: Dict[str, float]  # technical_capability, capital, human


@attrs.define
class EspionageAction:
    """Details for espionage action."""
    target_character: str
    budget: float
    focus: str  # What information to try to gather


@attrs.define
class MessageAction:
    """Details for sending a private message."""
    to_character: str
    content: str


@attrs.define
class ResearchStrategyPlayerProposedMove(PlayerProposedMove):
    """Player proposed move for wargame simulation.
    This can contain multiple actions and messages.
    """
    # Action-specific data
    action_type: Optional[ActionType] = None
    research_project: Optional[ResearchProjectAction] = None
    project_name_to_cancel: Optional[str] = None
    capital_investment: Optional[float] = None
    capital_to_sell: Optional[float] = None
    espionage: Optional[EspionageAction] = None
    poaching_target: Optional[str] = None
    poaching_budget: Optional[float] = None
    lobbying_message: Optional[str] = None
    lobbying_budget: Optional[float] = None
    marketing_message: Optional[str] = None
    marketing_budget: Optional[float] = None
    message: Optional[MessageAction] = None
    fundraising_amount: Optional[float] = None
    fundraising_description: Optional[str] = None

    # Support for multiple actions (list of moves)
    additional_actions: List["ResearchStrategyPlayerProposedMove"] = attrs.field(factory=list)

    def to_dict(self) -> Dict:
        """Convert move to dictionary for serialization."""
        result = {}
        if self.action_type:
            result["action_type"] = self.action_type.value
        if self.research_project:
            result["research_project"] = {
                "name": self.research_project.name,
                "description": self.research_project.description,
                "target_completion_date": self.research_project.target_completion_date,
                "annual_budget": self.research_project.annual_budget,
                "required_assets": self.research_project.required_assets,
            }
        optional_fields = [
            "project_name_to_cancel", "capital_investment", "capital_to_sell",
            "poaching_target", "poaching_budget", "lobbying_message", "lobbying_budget",
            "marketing_message", "marketing_budget", "fundraising_amount", "fundraising_description",
        ]
        for field in optional_fields:
            value = getattr(self, field, None)
            if value is not None:
                result[field] = value
        if self.espionage:
            result["espionage"] = {
                "target_character": self.espionage.target_character,
                "budget": self.espionage.budget,
                "focus": self.espionage.focus,
            }
        if self.message:
            result["message"] = {
                "to_character": self.message.to_character,
                "content": self.message.content,
            }
        return result
    
    def to_str(self) -> str:
        action_as_dict = self.to_dict()
        return pprint.pformat(action_as_dict, indent=1)


class ResearchStrategyPlayer(Player):
    """Player for wargame simulation using LLM agents."""

    def __init__(
            self,
            name: str,
            attributes: ResearchStrategyPlayerState,
            llm_client: Any,
            system_message_template: Optional[str] = None,
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

        # Build system message
        self.system_message = self._build_system_message(system_message_template)

        # Clean name for autogen (no special chars)
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

You must respond with a JSON object containing:
1. "actions": A list of actions you want to take this round
2. "messages": A list of private messages to send to other characters (optional)

### Action Format

Each action in "actions" should be one of the following (given in alphabetical order)
- {{"type": "cancel_research_project", "project_name": "<str>"}}
- {{"type": "create_research_project", "project": {{"name": "<str>", "description": "<str>", "target_completion_date": "<ISO date>", "annual_budget": <float>, "required_assets": {{"technical_capability": <float>, "capital": <float>, "human": <float>}}}}}}
Note: A more concrete, realistic, and well-scoped project is more likely to be approved. Allocate a _subset_ of your _current_ technical capability, capital, and human resources. Projects needing more resources than you currently have will not be approved.
- {{"type": "espionage", "target": "<character name>", "budget": <float>, "focus": "<what to investigate>"}}
- {{"type": "fundraise", "amount": <float>, "description": "<str>"}}
- {{"type": "invest_capital", "amount": <float>}}
- {{"type": "lobby", "message": "<str>", "budget": <float>}}
- {{"type": "marketing", "message": "<str>", "budget": <float>}}
- {{"type": "poach_talent", "target": "<character name>", "budget": <float>}}
- {{"type": "sell_capital", "amount": <float>}}

Consider being more conservative in initial research project budgets—if the budget is too high, the project won't be approved!

### Message Format

Each message in "messages" should be:
{{"to": "<character name>", "content": "<message text>"}}

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
                if p.name == project.name:
                    self.attributes.private_info.projects[i] = project
                    break

        for project_name in updates.completed_projects:
            for project in self.attributes.private_info.projects:
                if project.name == project_name:
                    project.status = "completed"
                    break

        for project_name in updates.cancelled_projects:
            for project in self.attributes.private_info.projects:
                if project.name == project_name:
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

    def propose_actions(self) -> List[ResearchStrategyPlayerProposedMove]:
        """Propose actions using LLM."""
        # This will be called by the gamemaster with appropriate context
        # For now, return empty move - the gamemaster will provide context
        return ResearchStrategyPlayerProposedMove()

    def propose_actions_with_context(
            self,
            game_state_summary: str,
            private_updates: str,
            current_date: datetime.datetime,
            round_number: int,
    ) -> List[ResearchStrategyPlayerProposedMove]:
        """Propose actions with full game context."""
        prompt = self._build_prompt(
            game_state_summary, private_updates, current_date, round_number
        )

        #NOTE: this is where we send the LLM the raw prompt
        response = self._get_llm_response_blocking(prompt)

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
4. **Espionage** - Gather intelligence on other characters
5. **Fundraising** - Request budget increases or raise capital
6. **Lobbying** - Influence public opinion and policy (may backfire)
7. **Marketing** - Promote your position publicly
8. **Poach Talent** - Attempt to recruit from one of the other organizations: Amber Systems, Blue Azure AI, or Crimson Labs
9. **Private Messages** - Negotiate with other characters directly
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
                    f"- {project.name}: {project.progress * 100:.0f}% complete, "
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
            return json.dumps({
                "actions": [],
                "messages": []
            })

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

    def _parse_response(self, response_text: str, round_number:int=None) -> List[ResearchStrategyPlayerProposedMove]:
        """Parse agent/LLM response into ResearchStrategyPlayerProposedMove."""
        # Try to extract JSON from response
        logger.debug(f"raw LLM response: {response_text}")
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(f"{self.name} - Could not parse response as JSON: {response_text}")
                return ResearchStrategyPlayerProposedMove()
        else:
            data = json.loads(json_match.group())

        # Parse actions
        actions_data = data.get("actions", [])
        messages_data = data.get("messages", [])

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self.name} - Parsed {len(actions_data)} actions, {len(messages_data)} messages")
        
        script_logger.info({"round" : round_number, "log_type" : "raw_llm_actions_messages",
                    "player" : self.name, "llm_response" : data})
        
        # Create moves from actions
        moves = []
        for action_dict in actions_data:
            move = self._create_move_from_dict(action_dict, messages_data)
            if move.action_type:  # Only add if valid
                moves.append(move)

        if moves:
            return moves
        else:
            return []

    def _create_move_from_dict(
            self, action_dict: Dict, messages: List[Dict]
    ) -> ResearchStrategyPlayerProposedMove:
        """Create a ResearchStrategyPlayerProposedMove from a dictionary."""
        action_type_map = {
            "fundraise": ActionType.FUNDRAISE,
            "create_research_project": ActionType.CREATE_RESEARCH_PROJECT,
            "cancel_research_project": ActionType.CANCEL_RESEARCH_PROJECT,
            "invest_capital": ActionType.INVEST_CAPITAL,
            "sell_capital": ActionType.SELL_CAPITAL,
            "espionage": ActionType.ESPIONAGE,
            "poach_talent": ActionType.POACH_TALENT,
            "lobby": ActionType.LOBBY,
            "marketing": ActionType.MARKETING,
        }

        action_type_str = action_dict.get("type", "")
        action_type = action_type_map.get(action_type_str)

        move = ResearchStrategyPlayerProposedMove(action_type=action_type)

        # Fill in action-specific fields
        if action_type == ActionType.FUNDRAISE:
            move.fundraising_amount = action_dict.get("amount")
            move.fundraising_description = action_dict.get("description")
        elif action_type == ActionType.CREATE_RESEARCH_PROJECT:
            project_data = action_dict.get("project", {})
            move.research_project = ResearchProjectAction(
                name=project_data.get("name", ""),
                description=project_data.get("description", ""),
                target_completion_date=project_data.get("target_completion_date", ""),
                annual_budget=project_data.get("annual_budget", 0.0),
                required_assets=project_data.get("required_assets", {}),
            )
        elif action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            move.project_name_to_cancel = action_dict.get("project_name")
        elif action_type == ActionType.INVEST_CAPITAL:
            move.capital_investment = action_dict.get("amount")
        elif action_type == ActionType.SELL_CAPITAL:
            move.capital_to_sell = action_dict.get("amount")
        elif action_type == ActionType.ESPIONAGE:
            esp_data = action_dict
            move.espionage = EspionageAction(
                target_character=esp_data.get("target") or esp_data.get("target_character", ""),
                budget=esp_data.get("budget", 0.0),
                focus=esp_data.get("focus", ""),
            )
        elif action_type == ActionType.POACH_TALENT:
            move.poaching_target = action_dict.get("target")
            move.poaching_budget = action_dict.get("budget")
        elif action_type == ActionType.LOBBY:
            move.lobbying_message = action_dict.get("message")
            move.lobbying_budget = action_dict.get("budget")
        elif action_type == ActionType.MARKETING:
            move.marketing_message = action_dict.get("message")
            move.marketing_budget = action_dict.get("budget")

        # Handle messages (attach first message to this move)
        if messages:
            first_message = messages[0]
            move.message = MessageAction(
                to_character=first_message.get("to", ""),
                content=first_message.get("content", ""),
            )

        return move

    def correct_moves(
            self, move_modifications: MoveCorrectionMessage, round_number:int=None
    ) -> ResearchStrategyPlayerProposedMove:
        """Correct moves based on gamemaster feedback."""
        logger.info(f"{self.name} - Proposed action failed: {move_modifications.error_message}")

        response = self._get_llm_response_blocking(f"Your proposed move described below was rejected, due to the following reason: {move_modifications.error_message}.  Please propose a single corrected move. {move_modifications.original_move.to_str()}")
        script_logger.info({"round" : round_number,"log_type" : "gm_action_correction", 
                            "player" : self.name, "status" : "fail", 
                            "original_move" : move_modifications.original_move.to_dict(),
                            "correction" :  move_modifications.error_message})

        return self._parse_response(response)


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
    
    # Game dynamics parameters (can be overridden)
    fundraising_success_rate: float = 0.7
    fundraising_efficiency: float = 0.8  # Percentage of requested amount received
    espionage_base_success_rate: float = 0.3
    espionage_budget_scaling: float = 1000000.0  # Budget per unit of success rate
    espionage_max_success_rate: float = 0.8
    poaching_base_success_rate: float = 0.2
    poaching_budget_scaling: float = 500000.0
    poaching_max_success_rate: float = 0.6
    poaching_transfer_rate: float = 0.1  # Percentage of target's human resources transferred
    lobbying_backfire_rate: float = 0.1
    capital_investment_efficiency: float = 0.9  # Budget to capital conversion
    capital_sale_efficiency: float = 0.7  # Capital to budget conversion
    research_progress_rate_base: float = 0.1
    research_progress_rate_max: float = 0.3
    research_human_scaling: float = 100.0  # Human resources per unit of progress rate
    information_leak_probability: float = 0.05
    random_event_probability: float = 0.1
    
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
    
    def get_player_move(self, player: ResearchStrategyPlayer) -> List[ResearchStrategyPlayerProposedMove]:
        """Get validated move from player, with correction loop."""
        # NOTE: for now, loop through all proposed moves once and allow the agent one retry for any invalid move
        max_attempts = 3
        
        # Build context for player
        game_state_summary = self._create_game_state_summary()
        private_updates = self._create_private_updates_summary(player)
        
        # TODO: Do we want an outer validation loop in case of general JSON failures?
        moves_to_validate = player.propose_actions_with_context(
            game_state_summary=game_state_summary,
            private_updates=private_updates,
            current_date=self.game_state.current_date,
            round_number=self.game_state.round_number,
        )

        valid_moves = []
        n_attempts = 0
        while len(moves_to_validate) > 0 and n_attempts < max_attempts:
            n_attempts += 1
            current_move_index = 0
            while current_move_index < len(moves_to_validate):
                candidate_move = moves_to_validate[current_move_index]

                if not candidate_move.action_type:
                    logger.debug("empty move")
                    moves_to_validate.pop(current_move_index)
                    current_move_index += 1
                    continue

                validation_error = self._validate_move(player, candidate_move)

                if validation_error is None:
                    candidate_move = moves_to_validate.pop(current_move_index)  # Because the list shrinks, don't need to update the index
                    valid_moves.append(candidate_move)
                else:
                    correction = MoveCorrectionMessage(
                        original_move=candidate_move,
                        error_message=validation_error
                    )
                    logger.debug("Requesting correction: "+ validation_error)
                    updated_move = player.correct_moves(correction)[0]
                    moves_to_validate[current_move_index] = updated_move
                    current_move_index += 1
        return valid_moves
    
    def _validate_move(self, player: ResearchStrategyPlayer, move: ResearchStrategyPlayerProposedMove) -> Optional[str]:
        """Validate a player's move. Returns error message if invalid, None if valid."""
        if not move.action_type:
            return None  # Empty move is valid (no action)
        
        # Check if player exists
        player_state = player.attributes
        
        # Validate based on action type
        if move.action_type == ActionType.CREATE_RESEARCH_PROJECT:
            if not move.research_project:
                return "Research project creation requires project details"
            
            # Check resources
            required = AssetBalance(
                technical_capability=move.research_project.required_assets.get("technical_capability", 0),
                capital=move.research_project.required_assets.get("capital", 0),
                human=move.research_project.required_assets.get("human", 0),
            )
            
            current = player_state.private_info.true_asset_balance
            if (current.technical_capability < required.technical_capability or
                current.capital < required.capital or
                current.human < required.human):
                return f"Insufficient resources for research project '{move.research_project.name}'"
            
            # Check budget
            year = str(self.game_state.current_date.year)
            current_budget = player_state.private_info.budget.get(year, 0.0)
            if current_budget < move.research_project.annual_budget:
                return f"Insufficient budget for research project '{move.research_project.name}'"
        
        elif move.action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            if not move.project_name_to_cancel:
                return "Cancel action requires project name"
            # Check if project exists and is active
            found = False
            for project in player_state.private_info.projects:
                if project.name == move.project_name_to_cancel and project.status == "active":
                    found = True
                    break
            if not found:
                return f"Active research project '{move.project_name_to_cancel}' not found"
        
        elif move.action_type == ActionType.INVEST_CAPITAL:
            if not move.capital_investment or move.capital_investment <= 0:
                return "Capital investment requires positive amount"
            year = str(self.game_state.current_date.year)
            budget = player_state.private_info.budget.get(year, 0.0)
            if budget < move.capital_investment:
                return f"Insufficient budget for capital investment"
        
        elif move.action_type == ActionType.SELL_CAPITAL:
            if not move.capital_to_sell or move.capital_to_sell <= 0:
                return "Sell capital requires positive amount"
            if player_state.private_info.true_asset_balance.capital < move.capital_to_sell:
                return f"Insufficient capital to sell"
        
        elif move.action_type == ActionType.ESPIONAGE:
            if not move.espionage:
                return "Espionage action requires espionage details"
            if not move.espionage.target_character:
                return "Espionage requires target character"
            # Check if target exists
            target_exists = any(p.name == move.espionage.target_character for p in self.players)
            if not target_exists:
                return f"Target character '{move.espionage.target_character}' not found"
            if move.espionage.budget <= 0:
                return "Espionage requires positive budget"
            year = str(self.game_state.current_date.year)
            budget = player_state.private_info.budget.get(year, 0.0)
            if budget < move.espionage.budget:
                return "Insufficient budget for espionage"
        
        elif move.action_type == ActionType.POACH_TALENT:
            if not move.poaching_target:
                return "Poaching requires target character"
            if not move.poaching_budget or move.poaching_budget <= 0:
                return "Poaching requires positive budget"
            target_exists = any(p.name == move.poaching_target for p in self.players)
            if not target_exists:
                return f"Target character '{move.poaching_target}' not found"
            year = str(self.game_state.current_date.year)
            budget = player_state.private_info.budget.get(year, 0.0)
            if budget < move.poaching_budget:
                return "Insufficient budget for poaching"
        
        elif move.action_type == ActionType.LOBBY:
            if not move.lobbying_budget or move.lobbying_budget <= 0:
                return "Lobbying requires positive budget"
            year = str(self.game_state.current_date.year)
            budget = player_state.private_info.budget.get(year, 0.0)
            if budget < move.lobbying_budget:
                return "Insufficient budget for lobbying"
        
        elif move.action_type == ActionType.MARKETING:
            if not move.marketing_budget or move.marketing_budget <= 0:
                return "Marketing requires positive budget"
            year = str(self.game_state.current_date.year)
            budget = player_state.private_info.budget.get(year, 0.0)
            if budget < move.marketing_budget:
                return "Insufficient budget for marketing"
        
        elif move.action_type == ActionType.FUNDRAISE:
            if not move.fundraising_amount or move.fundraising_amount <= 0:
                return "Fundraising requires positive amount"
        
        elif move.action_type == ActionType.MESSAGE:
            if not move.message:
                return "Message action requires message details"
            if not move.message.to_character:
                return "Message requires recipient"
            target_exists = any(p.name == move.message.to_character for p in self.players)
            if not target_exists:
                return f"Recipient '{move.message.to_character}' not found"
        
        return None  # Valid move
    
    def simulate_one_round(
        self, game_state: ResearchStrategyGameState, actions: Dict[str, List[ResearchStrategyPlayerProposedMove]]
    ):
        """Simulate one round of the research strategy game."""
        # Step 1: Increment time
        game_state.increment_round()
        self.round_number = game_state.round_number
        
        # Step 2: Process messages
        self._process_messages(game_state, actions)
        
        # Step 3: Process character-specific actions
        action_results = {}
        for player_name, action_lists in actions.items():
            player = self._get_player_by_name(player_name)
            if player:
                player_results = []
                # TODO: does this have to be a nested list?
                for action_list in action_lists:
                    for action in action_list:
                        player_results.extend(self._process_action(game_state, player, action))
                # NOTE: this now returns a list of string results
                action_results[player_name] = player_results
        
        # Step 4: Update research projects
        self._update_research_projects(game_state)
        
        # Step 5: Simulate information leaks
        self._simulate_information_leaks(game_state)
        
        # Step 6: Introduce random events & fixed events
        self._introduce_random_events(game_state)
        self._introduce_fixed_events(game_state)
        
        # Step 7: Create update messages for all players (including espionage results)
        self._create_update_messages(game_state, action_results)
        
        # Step 8: Update timestamps
        self.current_time = game_state.current_date
    
    def _process_messages(
        self, game_state: ResearchStrategyGameState, actions: Dict[str, List[ResearchStrategyPlayerProposedMove]]
    ):
        """Process private messages between characters."""
        for player_name, moves in actions.items():
            for move in moves:
                for submove in move:
                    if submove.message:
                        target_player = self._get_player_by_name(submove.message.to_character)
                        if target_player:
                            message = Message(
                                from_character=player_name,
                                to_character=submove.message.to_character,
                                content=submove.message.content,
                                timestamp=game_state.current_date,
                                round_number=game_state.round_number,
                            )
                            target_player.attributes.add_message(message)
    
    def _process_action(
        self, game_state: ResearchStrategyGameState, player: ResearchStrategyPlayer, move: ResearchStrategyPlayerProposedMove
    ) -> List[str]:
        """Process a single action and return result descriptions."""
        # NOTE: currently no case where we return more than one string as the result? 
        results = []
        
        if not move.action_type:
            logger.debug(f"{player.name}: Empty action")
            script_logger.info({"round" : game_state.round_number, "log_type" : "empty_action", "player" : player.name})
            return results
        else:
            logger.info(f"{player.name} proposed action:\n{move.to_str()}")
            script_logger.info({"round" : game_state.round_number, "log_type" : "propose_action", "player" : player.name, "actions" : move.to_dict()})

        player_state = player.attributes
        
        if move.action_type == ActionType.FUNDRAISE:
            result = self._process_fundraising(player_state, move)
            results.append(result)
        elif move.action_type == ActionType.CREATE_RESEARCH_PROJECT:
            result = self._process_create_research(player_state, move, game_state)
            results.append(result)
        elif move.action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            result = self._process_cancel_research(player_state, move)
            results.append(result)
        elif move.action_type == ActionType.INVEST_CAPITAL:
            result = self._process_capital_investment(player_state, move)
            results.append(result)
        elif move.action_type == ActionType.SELL_CAPITAL:
            result = self._process_sell_capital(player_state, move)
            results.append(result)
        elif move.action_type == ActionType.ESPIONAGE:
            result = self._process_espionage(player_state, move, game_state)
            results.append(result)
        elif move.action_type == ActionType.POACH_TALENT:
            result = self._process_poaching(player_state, move, game_state)
            results.append(result)
        elif move.action_type == ActionType.LOBBY:
            result = self._process_lobbying(player_state, move)
            results.append(result)
        elif move.action_type == ActionType.MARKETING:
            result = self._process_marketing(player_state, move)
            results.append(result)
        
        # Process additional actions
        for additional_move in move.additional_actions:
            logger.error("we have additional actions again!")
            additional_results = self._process_action(game_state, player, additional_move)
            results.extend(additional_results)
        
        return results
    
    # Modular game dynamics methods (can be overridden)
    
    def _process_fundraising(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process fundraising action."""
        if not move.fundraising_amount:
            return "Fail:Fundraising action with no amount specified"
        
        success = self._random.random() < self.fundraising_success_rate
        
        if success:
            year = str(self.game_state.current_date.year)
            current_budget = player_state.private_info.budget.get(year, 0.0)
            amount_received = move.fundraising_amount * self.fundraising_efficiency
            player_state.private_info.budget[year] = current_budget + amount_received
            return f"Success:Fundraised ${amount_received:,.0f}"
        else:
            return f"Fail:Fundraising attempt for ${move.fundraising_amount:,.0f} was unsuccessful"
    
    def _process_create_research(
        self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove, game_state: ResearchStrategyGameState
    ) -> str:
        """Process research project creation."""
        if not move.research_project:
            return "Fail:Research project creation with no project details"
        
        project_data = move.research_project
        
        # Check if character has sufficient resources
        required = AssetBalance(
            technical_capability=project_data.required_assets.get("technical_capability", 0),
            capital=project_data.required_assets.get("capital", 0),
            human=project_data.required_assets.get("human", 0),
        )
        
        current = player_state.private_info.true_asset_balance
        
        if (current.technical_capability < required.technical_capability or
            current.capital < required.capital or
            current.human < required.human):
            return f"Fail:Insufficient resources to start research project '{project_data.name}'"
        
        # Check budget
        year = str(game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        if current_budget < project_data.annual_budget:
            return f"Fail:Insufficient budget for research project '{project_data.name}'"
        
        # Create project
        try:
            target_date = datetime.datetime.fromisoformat(project_data.target_completion_date)
        except ValueError:
            target_date = game_state.current_date + datetime.timedelta(days=365)
        
        project = ResearchProject(
            name=project_data.name,
            description=project_data.description,
            target_completion_date=target_date,
            committed_budget=project_data.annual_budget,
            committed_assets=required,
            status="active",
            progress=0.0,
        )
        
        # Assess realism
        project.realistic_goals = self._assess_research_realism(project, player_state)
        
        # Deduct resources
        player_state.private_info.true_asset_balance = current.subtract(required)
        player_state.private_info.budget[year] = current_budget - project_data.annual_budget
        
        # Add project
        player_state.private_info.projects.append(project)
        
        return f"Success:Created research project '{project_data.name}'"
    
    def _process_cancel_research(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process research project cancellation."""
        if not move.project_name_to_cancel:
            return "Fail:Cancel action with no project name"
        
        # Find and cancel project
        for project in player_state.private_info.projects:
            if project.name == move.project_name_to_cancel and project.status == "active":
                project.status = "cancelled"
                # Refund some resources (not all)
                refund = AssetBalance(
                    technical_capability=project.committed_assets.technical_capability * 0.5,
                    capital=project.committed_assets.capital * 0.5,
                    human=project.committed_assets.human * 0.5,
                )
                player_state.private_info.true_asset_balance = (
                    player_state.private_info.true_asset_balance.add(refund)
                )
                return f"Success:Cancelled research project '{move.project_name_to_cancel}'"
        
        return f"Fail:Could not find active research project '{move.project_name_to_cancel}'"
    
    def _process_capital_investment(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process capital investment."""
        if not move.capital_investment:
            return "Fail:Capital investment with no amount"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.capital_investment:
            return f"Fail:Insufficient budget for capital investment of ${move.capital_investment:,.0f}"
        
        # Invest: convert budget to capital assets
        player_state.private_info.budget[year] = budget - move.capital_investment
        capital_gained = move.capital_investment * self.capital_investment_efficiency
        player_state.private_info.true_asset_balance.capital += capital_gained
        
        return f"Success:Invested ${move.capital_investment:,.0f} in capital improvements"
    
    def _process_sell_capital(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process selling capital."""
        if not move.capital_to_sell:
            return "Fail:Sell capital with no amount"
        
        if player_state.private_info.true_asset_balance.capital < move.capital_to_sell:
            return f"Fail:Insufficient capital to sell ${move.capital_to_sell:,.0f}"
        
        # Sell: convert capital to budget
        player_state.private_info.true_asset_balance.capital -= move.capital_to_sell
        year = str(self.game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        budget_gained = move.capital_to_sell * self.capital_sale_efficiency
        player_state.private_info.budget[year] = current_budget + budget_gained
        
        return f"Success:Sold ${move.capital_to_sell:,.0f} in capital assets"
    
    def _process_espionage(
        self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove, game_state: ResearchStrategyGameState
    ) -> str:
        """Process espionage action."""
        if not move.espionage:
            return "Fail:Espionage action with no details"
        
        target_player = self._get_player_by_name(move.espionage.target_character)
        if not target_player:
            return f"Fail:Espionage target '{move.espionage.target_character}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.espionage.budget:
            return "Fail:Insufficient budget for espionage"
        
        # Deduct budget
        player_state.private_info.budget[year] = budget - move.espionage.budget
        
        # Store espionage attempt (results processed later)
        success_prob = min(
            self.espionage_base_success_rate + (move.espionage.budget / self.espionage_budget_scaling),
            self.espionage_max_success_rate
        )
        success = self._random.random() < success_prob
        
        player_state.private_info.espionage.append({
            "target": move.espionage.target_character,
            "focus": move.espionage.focus,
            "budget": move.espionage.budget,
            "success": success,
            "round": game_state.round_number,
        })
        logger.debug(f"Espionage: {player_state.private_info.espionage}")
        
        return f"{'Success' if success else 'Fail'}:Conducted espionage on {move.espionage.target_character}"
    
    def _process_poaching(
        self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove, game_state: ResearchStrategyGameState
    ) -> str:
        """Process talent poaching."""
        if not move.poaching_target or not move.poaching_budget:
            return "Fail:Poaching action with no target or budget"
        
        target_player = self._get_player_by_name(move.poaching_target)
        if not target_player:
            return f"Fail:target '{move.poaching_target}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.poaching_budget:
            return "Fail:Insufficient budget for poaching"
        
        # Deduct budget
        player_state.private_info.budget[year] = budget - move.poaching_budget
        
        # Determine success
        success_prob = min(
            self.poaching_base_success_rate + (move.poaching_budget / self.poaching_budget_scaling),
            self.poaching_max_success_rate
        )
        success = self._random.random() < success_prob
        
        if success:
            # Transfer some human resources
            transfer_amount = min(
                target_player.attributes.private_info.true_asset_balance.human * self.poaching_transfer_rate,
                5.0
            )
            target_player.attributes.private_info.true_asset_balance.human -= transfer_amount
            player_state.private_info.true_asset_balance.human += transfer_amount
            return f"Success:Poached talent from {move.poaching_target} (gained {transfer_amount:.1f} human resources)"
        else:
            return f"Fail:Poaching attempt on {move.poaching_target}"
    
    def _process_lobbying(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process lobbying action."""
        if not move.lobbying_message or not move.lobbying_budget:
            return "Fail:Lobbying action with no message or budget"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.lobbying_budget:
            return "Fail:Insufficient budget for lobbying"
        
        player_state.private_info.budget[year] = budget - move.lobbying_budget
        
        # Lobbying may backfire
        if self._random.random() < self.lobbying_backfire_rate:
            return f"Fail:Lobbying campaign backfired: {move.lobbying_message}"
        else:
            return f"Success:Launched lobbying campaign: {move.lobbying_message}"
    
    def _process_marketing(self, player_state: ResearchStrategyPlayerState, move: ResearchStrategyPlayerProposedMove) -> str:
        """Process marketing action."""
        if not move.marketing_message or not move.marketing_budget:
            return "Fail:Marketing action with no message or budget"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.marketing_budget:
            return "Fail:Insufficient budget for marketing"
        
        player_state.private_info.budget[year] = budget - move.marketing_budget
        return f"Success:Launched marketing campaign: {move.marketing_message}"
    
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
    
    # TODO: I think ok to remove this?
    def _simulate_espionage_results(self, game_state: ResearchStrategyGameState):
        """Process espionage results and add to player private updates."""
        for player in self.players:
            player_state = player.attributes
            if player_state.private_info.espionage:
                for esp_result in player_state.private_info.espionage:
                    if esp_result and "success" in esp_result and esp_result["success"]:
                        target_player = self._get_player_by_name(esp_result["target"])
                        if target_player:
                            # Store for later inclusion in update message
                            #f not hasattr(player_state, '_private_updates'):
                            #    player_state._private_updates = []
                            player_state.private_updates.append(
                                f"Espionage on {esp_result['target']} ({esp_result['focus']}): "
                                f"Discovered budget ≈${target_player.attributes.private_info.budget.get(str(game_state.current_date.year), 0):,.0f}, "
                                f"assets: tech={target_player.attributes.private_info.true_asset_balance.technical_capability:.1f}, "
                                f"capital={target_player.attributes.private_info.true_asset_balance.capital:.1f}, "
                                f"human={target_player.attributes.private_info.true_asset_balance.human:.1f}"
                            )
                # Clear processed results
                # NOTE: why clear...? only a temporary record?
                #player_state.private_info.espionage = []
    
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
    
    def _assess_research_realism(
        self, project: ResearchProject, player_state: ResearchStrategyPlayerState
    ) -> Optional[str]:
        """Assess if research goals are realistic and modify if needed."""
        days_to_complete = (project.target_completion_date - datetime.datetime.now()).days
        required_resources = (
            project.committed_assets.human +
            project.committed_assets.technical_capability * 0.5 +
            project.committed_assets.capital * 0.3
        )
        
        # Rough estimate: need at least 10 resource-days per day of timeline
        if required_resources * days_to_complete < days_to_complete * 10:
            # Extend timeline
            project.target_completion_date = datetime.datetime.now() + datetime.timedelta(days=365)
            return "Timeline extended to be more realistic given available resources."
        
        return None
    
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
                    updates.completed_projects.append(project.name)
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
    
    def _create_private_updates_summary(self, player: ResearchStrategyPlayer) -> str:
        """Create summary of private updates for a player."""
        updates = []
        
        # Add research project updates
        for project in player.attributes.private_info.projects:
            if project.status == "completed":
                updates.append(f"Research project '{project.name}' has been completed!")
            elif project.status == "active":
                updates.append(
                    f"Research project '{project.name}' is {project.progress*100:.0f}% complete."
                )

        for esp_result in player.attributes.private_info.espionage:
            if  "success" in esp_result and esp_result["success"]:
                target_player = self._get_player_by_name(esp_result["target"])
                if target_player:
                    updates.append(
                        f"Espionage on {esp_result['target']} ({esp_result['focus']}): "
                        # TODO: how to properly pass this?
                        #f"Discovered budget ≈${target_player.attributes.private_info.budget.get(str(game_state.current_date.year), 0):,.0f}, "
                        f"assets: tech={target_player.attributes.private_info.true_asset_balance.technical_capability:.1f}, "
                        f"capital={target_player.attributes.private_info.true_asset_balance.capital:.1f}, "
                        f"human={target_player.attributes.private_info.true_asset_balance.human:.1f}"
            )
        
        return "\n".join(updates) if updates else "No significant private updates."
    
    def _get_player_by_name(self, name: str) -> Optional[ResearchStrategyPlayer]:
        """Get player by name."""
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
    
    def run_simulation(self):
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
                per_player_actions = self.get_player_move(player)
                actions[player.name] = [per_player_actions]
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

