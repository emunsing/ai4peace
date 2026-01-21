"""Wargame gamemaster implementation with modular game dynamics."""

import datetime
import random
import logging
from typing import Dict, List, Optional, Any
import attrs

from .new_architecture_draft import GenericGameMaster
from .wargame_state import (
    WargameGameState,
    WargamePlayerState,
    AssetBalance,
    ResearchProject,
    Message,
)
from .wargame_actions import (
    WargamePlayerProposedMove,
    WargameMoveCorrectionMessage,
    ActionType,
)
from .wargame_updates import (
    WargameGamemasterUpdateMessage,
    WargamePlayerStateUpdates,
)
from .wargame_player import WargamePlayer

logger = logging.getLogger(__name__)


@attrs.define
class WargameGameMaster(GenericGameMaster):
    """Game master for wargame simulation with modular game dynamics."""
    
    players: List[WargamePlayer] = attrs.field(factory=list)
    current_time: datetime.datetime = attrs.field(factory=datetime.datetime.now)
    default_timestep: datetime.timedelta = attrs.field(factory=lambda: datetime.timedelta(days=90))
    current_gamemaster_updates: Dict[str, WargameGamemasterUpdateMessage] = attrs.field(factory=dict)
    game_state: WargameGameState = attrs.field(factory=lambda: WargameGameState(
        current_date=datetime.datetime.now(),
        round_number=0,
    ))
    round_number: int = 0
    random_seed: Optional[int] = None
    random_events: List[str] = attrs.field(factory=list)
    
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
    
    def create_player_update_messages(self, player: WargamePlayer) -> WargameGamemasterUpdateMessage:
        """Create update message for a player."""
        # Get public views of other players
        other_players_public_views = {}
        for other_player in self.players:
            if other_player.name != player.name:
                other_players_public_views[other_player.name] = other_player.attributes.public_view
        
        # Create empty state updates (will be filled during simulation)
        state_updates = WargamePlayerStateUpdates(
            other_players_public_views=other_players_public_views,
            public_events=self.game_state.public_events[-5:],  # Last 5 events
        )
        
        return WargameGamemasterUpdateMessage(
            last_action_timestamp=self.current_time,
            next_action_timestamp=self.current_time + self.get_timestep(),
            state_updates=state_updates
        )
    
    def get_player_move(self, player: WargamePlayer) -> WargamePlayerProposedMove:
        """Get validated move from player, with correction loop."""
        max_attempts = 5
        
        # Build context for player
        game_state_summary = self._create_game_state_summary()
        private_updates = self._create_private_updates_summary(player)
        
        for attempt in range(max_attempts):
            # Get move from player (using async method)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            move = loop.run_until_complete(
                player.propose_actions_with_context(
                    game_state_summary=game_state_summary,
                    private_updates=private_updates,
                    current_date=self.game_state.current_date,
                    round_number=self.game_state.round_number,
                )
            )
            
            # Validate move
            validation_error = self._validate_move(player, move)
            if validation_error is None:
                return move
            
            # Create correction message
            correction = WargameMoveCorrectionMessage(
                error_message=validation_error
            )
            
            # Get corrected move (synchronous)
            move = player.correct_moves(correction)
            
            # Validate again
            validation_error = self._validate_move(player, move)
            if validation_error is None:
                return move
            
            logger.warning(f"{player.name} - Invalid move (attempt {attempt + 1}/{max_attempts}): {validation_error}")
        
        # If we get here, return the last move anyway (game will handle it)
        logger.error(f"{player.name} - Failed to get valid move after {max_attempts} attempts")
        return move
    
    def _validate_move(self, player: WargamePlayer, move: WargamePlayerProposedMove) -> Optional[str]:
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
        self, game_state: WargameGameState, actions: Dict[str, WargamePlayerProposedMove]
    ):
        """Simulate one round of the wargame."""
        # Step 1: Increment time
        game_state.increment_round()
        self.round_number = game_state.round_number
        
        # Step 2: Process messages
        self._process_messages(game_state, actions)
        
        # Step 3: Process character-specific actions
        action_results = {}
        for player_name, move in actions.items():
            player = self._get_player_by_name(player_name)
            if player:
                results = self._process_action(game_state, player, move)
                action_results[player_name] = results
        
        # Step 4: Update research projects
        self._update_research_projects(game_state)
        
        # Step 5: Simulate espionage results
        self._simulate_espionage_results(game_state)
        
        # Step 6: Simulate information leaks
        self._simulate_information_leaks(game_state)
        
        # Step 7: Introduce random events
        self._introduce_random_events(game_state)
        
        # Step 8: Create update messages for all players
        self._create_update_messages(game_state, action_results)
        
        # Step 9: Update timestamps
        self.current_time = game_state.current_date
    
    def _process_messages(
        self, game_state: WargameGameState, actions: Dict[str, WargamePlayerProposedMove]
    ):
        """Process private messages between characters."""
        for player_name, move in actions.items():
            if move.message:
                target_player = self._get_player_by_name(move.message.to_character)
                if target_player:
                    message = Message(
                        from_character=player_name,
                        to_character=move.message.to_character,
                        content=move.message.content,
                        timestamp=game_state.current_date,
                        round_number=game_state.round_number,
                    )
                    target_player.attributes.add_message(message)
    
    def _process_action(
        self, game_state: WargameGameState, player: WargamePlayer, move: WargamePlayerProposedMove
    ) -> List[str]:
        """Process a single action and return result descriptions."""
        results = []
        
        if not move.action_type:
            return results
        
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
            additional_results = self._process_action(game_state, player, additional_move)
            results.extend(additional_results)
        
        return results
    
    # Modular game dynamics methods (can be overridden)
    
    def _process_fundraising(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process fundraising action."""
        if not move.fundraising_amount:
            return "Fundraising action with no amount specified"
        
        success = self._random.random() < self.fundraising_success_rate
        
        if success:
            year = str(self.game_state.current_date.year)
            current_budget = player_state.private_info.budget.get(year, 0.0)
            amount_received = move.fundraising_amount * self.fundraising_efficiency
            player_state.private_info.budget[year] = current_budget + amount_received
            return f"Successfully raised ${amount_received:,.0f}"
        else:
            return f"Fundraising attempt for ${move.fundraising_amount:,.0f} was unsuccessful"
    
    def _process_create_research(
        self, player_state: WargamePlayerState, move: WargamePlayerProposedMove, game_state: WargameGameState
    ) -> str:
        """Process research project creation."""
        if not move.research_project:
            return "Research project creation with no project details"
        
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
            return f"Insufficient resources to start research project '{project_data.name}'"
        
        # Check budget
        year = str(game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        if current_budget < project_data.annual_budget:
            return f"Insufficient budget for research project '{project_data.name}'"
        
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
        
        return f"Created research project '{project_data.name}'"
    
    def _process_cancel_research(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process research project cancellation."""
        if not move.project_name_to_cancel:
            return "Cancel action with no project name"
        
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
                return f"Cancelled research project '{move.project_name_to_cancel}'"
        
        return f"Could not find active research project '{move.project_name_to_cancel}'"
    
    def _process_capital_investment(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process capital investment."""
        if not move.capital_investment:
            return "Capital investment with no amount"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.capital_investment:
            return f"Insufficient budget for capital investment of ${move.capital_investment:,.0f}"
        
        # Invest: convert budget to capital assets
        player_state.private_info.budget[year] = budget - move.capital_investment
        capital_gained = move.capital_investment * self.capital_investment_efficiency
        player_state.private_info.true_asset_balance.capital += capital_gained
        
        return f"Invested ${move.capital_investment:,.0f} in capital improvements"
    
    def _process_sell_capital(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process selling capital."""
        if not move.capital_to_sell:
            return "Sell capital with no amount"
        
        if player_state.private_info.true_asset_balance.capital < move.capital_to_sell:
            return f"Insufficient capital to sell ${move.capital_to_sell:,.0f}"
        
        # Sell: convert capital to budget
        player_state.private_info.true_asset_balance.capital -= move.capital_to_sell
        year = str(self.game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        budget_gained = move.capital_to_sell * self.capital_sale_efficiency
        player_state.private_info.budget[year] = current_budget + budget_gained
        
        return f"Sold ${move.capital_to_sell:,.0f} in capital assets"
    
    def _process_espionage(
        self, player_state: WargamePlayerState, move: WargamePlayerProposedMove, game_state: WargameGameState
    ) -> str:
        """Process espionage action."""
        if not move.espionage:
            return "Espionage action with no details"
        
        target_player = self._get_player_by_name(move.espionage.target_character)
        if not target_player:
            return f"Target character '{move.espionage.target_character}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.espionage.budget:
            return f"Insufficient budget for espionage"
        
        # Deduct budget
        player_state.private_info.budget[year] = budget - move.espionage.budget
        
        # Store espionage attempt (results processed later)
        success_prob = min(
            self.espionage_base_success_rate + (move.espionage.budget / self.espionage_budget_scaling),
            self.espionage_max_success_rate
        )
        success = self._random.random() < success_prob
        
        # Store in player metadata
        if not hasattr(player_state, '_espionage_results'):
            player_state._espionage_results = []
        
        player_state._espionage_results.append({
            "target": move.espionage.target_character,
            "focus": move.espionage.focus,
            "budget": move.espionage.budget,
            "success": success,
            "round": game_state.round_number,
        })
        
        return f"Conducted espionage on {move.espionage.target_character} ({'success' if success else 'failed'})"
    
    def _process_poaching(
        self, player_state: WargamePlayerState, move: WargamePlayerProposedMove, game_state: WargameGameState
    ) -> str:
        """Process talent poaching."""
        if not move.poaching_target or not move.poaching_budget:
            return "Poaching action with no target or budget"
        
        target_player = self._get_player_by_name(move.poaching_target)
        if not target_player:
            return f"Target character '{move.poaching_target}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.poaching_budget:
            return "Insufficient budget for poaching"
        
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
            return f"Successfully poached talent from {move.poaching_target} (gained {transfer_amount:.1f} human resources)"
        else:
            return f"Poaching attempt on {move.poaching_target} failed"
    
    def _process_lobbying(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process lobbying action."""
        if not move.lobbying_message or not move.lobbying_budget:
            return "Lobbying action with no message or budget"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.lobbying_budget:
            return "Insufficient budget for lobbying"
        
        player_state.private_info.budget[year] = budget - move.lobbying_budget
        
        # Lobbying may backfire
        if self._random.random() < self.lobbying_backfire_rate:
            return f"Lobbying campaign backfired: {move.lobbying_message[:50]}..."
        else:
            return f"Launched lobbying campaign: {move.lobbying_message[:50]}..."
    
    def _process_marketing(self, player_state: WargamePlayerState, move: WargamePlayerProposedMove) -> str:
        """Process marketing action."""
        if not move.marketing_message or not move.marketing_budget:
            return "Marketing action with no message or budget"
        
        year = str(self.game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < move.marketing_budget:
            return "Insufficient budget for marketing"
        
        player_state.private_info.budget[year] = budget - move.marketing_budget
        return f"Launched marketing campaign: {move.marketing_message[:50]}..."
    
    def _update_research_projects(self, game_state: WargameGameState):
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
    
    def _simulate_espionage_results(self, game_state: WargameGameState):
        """Process espionage results and add to player private updates."""
        for player in self.players:
            player_state = player.attributes
            if hasattr(player_state, '_espionage_results'):
                for esp_result in player_state._espionage_results:
                    if esp_result.get("success"):
                        target_player = self._get_player_by_name(esp_result["target"])
                        if target_player:
                            # Store for later inclusion in update message
                            if not hasattr(player_state, '_private_updates'):
                                player_state._private_updates = []
                            player_state._private_updates.append(
                                f"Espionage on {esp_result['target']} ({esp_result['focus']}): "
                                f"Discovered budget ≈${target_player.attributes.private_info.budget.get(str(game_state.current_date.year), 0):,.0f}, "
                                f"assets: tech={target_player.attributes.private_info.true_asset_balance.technical_capability:.1f}, "
                                f"capital={target_player.attributes.private_info.true_asset_balance.capital:.1f}, "
                                f"human={target_player.attributes.private_info.true_asset_balance.human:.1f}"
                            )
                # Clear processed results
                player_state._espionage_results = []
    
    def _simulate_information_leaks(self, game_state: WargameGameState):
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
    
    def _introduce_random_events(self, game_state: WargameGameState):
        """Introduce random external events."""
        if self._random.random() < self.random_event_probability and self.random_events:
            event = self._random.choice(self.random_events)
            game_state.public_events.append(f"Round {game_state.round_number}: {event}")
    
    def _assess_research_realism(
        self, project: ResearchProject, player_state: WargamePlayerState
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
        self, game_state: WargameGameState, action_results: Dict[str, List[str]]
    ):
        """Create update messages for all players."""
        # Create global action summary
        action_summary = self._create_action_summary(game_state, action_results)
        game_state.game_history.append(action_summary)
        
        # Create update messages for each player
        for player in self.players:
            updates = WargamePlayerStateUpdates()
            
            # Add action results
            if player.name in action_results:
                updates.action_results = action_results[player.name]
            
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
            update_msg = WargameGamemasterUpdateMessage(
                last_action_timestamp=self.current_time,
                next_action_timestamp=self.current_time + self.get_timestep(),
                state_updates=updates
            )
            
            self.current_gamemaster_updates[player.name] = update_msg
    
    def _create_action_summary(
        self, game_state: WargameGameState, action_results: Dict[str, List[str]]
    ) -> str:
        """Create a summary of all actions taken this round."""
        summary_parts = [f"Round {game_state.round_number} Summary ({game_state.current_date.strftime('%Y-%m-%d')}):"]
        
        for player_name, results in action_results.items():
            summary_parts.append(f"\n{player_name}:")
            for result in results:
                summary_parts.append(f"  - {result}")
        
        # Add public events
        if game_state.public_events:
            summary_parts.append("\nPublic Events:")
            for event in game_state.public_events[-5:]:
                summary_parts.append(f"  - {event}")
        
        return "\n".join(summary_parts)
    
    def _create_game_state_summary(self) -> str:
        """Create summary of global game state."""
        if self.game_state.game_history:
            return self.game_state.game_history[-1]
        return "Game starting..."
    
    def _create_private_updates_summary(self, player: WargamePlayer) -> str:
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
        
        return "\n".join(updates) if updates else "No significant private updates."
    
    def _get_player_by_name(self, name: str) -> Optional[WargamePlayer]:
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
                f"Capital={player.attributes.private_info.true_asset_balance.capital:.1f}, "
                f"Human={player.attributes.private_info.true_asset_balance.human:.1f}"
            )
    
    def run_simulation(self):
        """Run the full simulation."""
        logger.info("Starting wargame simulation")
        logger.info(f"Players: {[p.name for p in self.players]}")
        
        # Initial update messages for all players
        for player in self.players:
            update_msg = self.create_player_update_messages(player)
            player.update_state(update_msg)
            self.current_gamemaster_updates[player.name] = update_msg
        
        max_rounds = 100  # Safety limit
        round_count = 0
        
        while round_count < max_rounds:
            round_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Round {round_count}")
            logger.info(f"{'='*60}")
            
            # Get moves from all players
            actions = {}
            for player in self.players:
                move = self.get_player_move(player)
                actions[player.name] = move
            
            # Simulate the round
            self.simulate_one_round(self.game_state, actions)
            
            # Update all players with the new state
            for player in self.players:
                if player.name in self.current_gamemaster_updates:
                    player.update_state(self.current_gamemaster_updates[player.name])
            
            # Log current state
            self.log_game_state()
            
            # Check for game ending
            ending = self.get_game_ending()
            if ending:
                logger.info(f"\n{'='*60}")
                logger.info(f"Game Over: {ending}")
                logger.info(f"{'='*60}")
                break
        
        if round_count >= max_rounds:
            logger.warning(f"Game reached maximum rounds ({max_rounds})")

