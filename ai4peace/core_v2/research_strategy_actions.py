import abc
import datetime
import random
from enum import Enum
from typing import Optional, Dict, List
import logging
import attrs

# from ai4peace.core_v2 import ResearchStrategyGameState, ResearchStrategyPlayer, ResearchStrategyGameMaster, \
#     ResearchStrategyPlayerStateUpdates, ResearchStrategyPlayerState, AssetBalance, ResearchProject, Message

from ai4peace.core.utils import get_transcript_logger
from ai4peace.core_v2 import PlayerStateUpdates, PublicView

script_logger = get_transcript_logger()

logger = logging.getLogger(__name__)


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
    MESSAGE = "bilateral_message"  # Private message to another character


@attrs.define
class Action(abc.ABC):
    """Base class for all actions in the game."""
    initiating_character_name: str

    @property
    @abc.abstractmethod
    def action_type(self) -> ActionType:
        """Return the type of this action."""
        pass

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        """Validate the action is valid. Return None if valid, otherwise return an error message."""
        # Basic validation: check if player exists
        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"
        return None

    def _get_player_by_name(self, name: str, players: list["ResearchStrategyPlayer"]) -> Optional["ResearchStrategyPlayer"]:
        """Helper to get player by project_name."""
        for player in players:
            if player.name == name:
                return player
        return None

    @classmethod
    @abc.abstractmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Handle all actions of this type for a given round.

        Updates the game state and returns player state updates.
        This allows for batch processing of actions (e.g., clearing markets, resolving competition).
        """
        pass


@attrs.define
class FundraiseAction(Action):
    """Action to fundraise for additional budget."""
    amount: float
    description: Optional[str] = None

    # Action-specific parameters (class attributes, not init parameters)
    success_rate: float = 0.7
    efficiency: float = 0.8  # Percentage of requested amount received

    @property
    def action_type(self) -> ActionType:
        return ActionType.FUNDRAISE

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.amount or self.amount <= 0:
            return "Fundraising requires positive amount"
        return None

    @classmethod
    def _process_single_action(cls, action: "FundraiseAction", player_state: "ResearchStrategyPlayerState", game_state: "ResearchStrategyGameState", random_gen: random.Random) -> str:
        """Process a single fundraising action."""
        success = random_gen.random() < action.success_rate

        if success:
            year = str(game_state.current_date.year)
            current_budget = player_state.private_info.budget.get(year, 0.0)
            amount_received = action.amount * action.efficiency
            player_state.private_info.budget[year] = current_budget + amount_received
            return f"Success:Fundraised ${amount_received:,.0f}"
        else:
            return f"Fail:Fundraising attempt for ${action.amount:,.0f} was unsuccessful"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all fundraising actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, FundraiseAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state, gamemaster._random)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class CreateResearchProjectAction(Action):
    """Action to create a new research project."""
    project_name: str
    description: str
    target_completion_date: str  # ISO format date
    annual_budget: float
    required_assets: Dict[str, float]  # technical_capability, capital, human

    @property
    def action_type(self) -> ActionType:
        return ActionType.CREATE_RESEARCH_PROJECT

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        player_state = player.attributes

        # Check resources
        required = AssetBalance(
            technical_capability=self.required_assets.get("technical_capability", 0),
            capital=self.required_assets.get("capital", 0),
            human=self.required_assets.get("human", 0),
        )

        current = player_state.private_info.true_asset_balance
        if (current.technical_capability < required.technical_capability or
            current.capital < required.capital or
            current.human < required.human):
            return f"Insufficient resources for research project '{self.project_name}'"

        # Check budget
        year = str(game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        if current_budget < self.annual_budget:
            return f"Insufficient budget for research project '{self.project_name}'"

        return None

    @classmethod
    def _process_single_action(cls, action: "CreateResearchProjectAction", player_state: ResearchStrategyPlayerState, game_state: "ResearchStrategyGameState", assess_realism_callback) -> str:
        """Process a single research project creation action."""
        # Check if character has sufficient resources
        required = AssetBalance(
            technical_capability=action.required_assets.get("technical_capability", 0),
            capital=action.required_assets.get("capital", 0),
            human=action.required_assets.get("human", 0),
        )

        current = player_state.private_info.true_asset_balance

        if (current.technical_capability < required.technical_capability or
            current.capital < required.capital or
            current.human < required.human):
            return f"Fail:Insufficient resources to start research project '{action.project_name}'"

        # Check budget
        year = str(game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        if current_budget < action.annual_budget:
            return f"Fail:Insufficient budget for research project '{action.project_name}'"

        # Create project
        try:
            target_date = datetime.datetime.fromisoformat(action.target_completion_date)
        except ValueError:
            target_date = game_state.current_date + datetime.timedelta(days=365)

        project = ResearchProject(
            project_name=action.project_name,
            description=action.description,
            target_completion_date=target_date,
            committed_budget=action.annual_budget,
            committed_assets=required,
            status="active",
            progress=0.0,
        )

        # Assess realism (using callback to gamemaster method)
        if assess_realism_callback:
            project.realistic_goals = assess_realism_callback(project, player_state)

        # Deduct resources
        player_state.private_info.true_asset_balance = current.subtract(required)
        player_state.private_info.budget[year] = current_budget - action.annual_budget

        # Add project
        player_state.private_info.projects.append(project)

        return f"Success:Created research project '{action.project_name}'"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all research project creation actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, CreateResearchProjectAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state, cls._assess_research_realism)
            updates[player.name].action_results.append(result)

        return updates

    @staticmethod
    def _assess_research_realism(
            project: ResearchProject, player_state: ResearchStrategyPlayerState
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


@attrs.define
class CancelResearchProjectAction(Action):
    """Action to cancel an active research project."""
    project_name: str

    # Action-specific parameters (class attributes)
    refund_rate: float = 0.5  # Percentage of resources refunded when cancelling

    @property
    def action_type(self) -> ActionType:
        return ActionType.CANCEL_RESEARCH_PROJECT

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.project_name:
            return "Cancel action requires project project_name"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        # Check if project exists and is active
        found = False
        for project in player.attributes.private_info.projects:
            if project.project_name == self.project_name and project.status == "active":
                found = True
                break
        if not found:
            return f"Active research project '{self.project_name}' not found"

        return None

    @classmethod
    def _process_single_action(cls, action: "CancelResearchProjectAction", player_state: ResearchStrategyPlayerState, game_state: ResearchStrategyGameState) -> str:
        """Process a single research project cancellation action."""
        # Find and cancel project
        for project in player_state.private_info.projects:
            if project.project_name == action.project_name and project.status == "active":
                project.status = "cancelled"
                # Refund some resources (not all)
                refund = AssetBalance(
                    technical_capability=project.committed_assets.technical_capability * action.refund_rate,
                    capital=project.committed_assets.capital * action.refund_rate,
                    human=project.committed_assets.human * action.refund_rate,
                )
                player_state.private_info.true_asset_balance = (
                    player_state.private_info.true_asset_balance.add(refund)
                )
                return f"Success:Cancelled research project '{action.project_name}'"

        return f"Fail:Could not find active research project '{action.project_name}'"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all research project cancellation actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, CancelResearchProjectAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class InvestCapitalAction(Action):
    """Action to invest budget into capital assets."""
    amount: float

    # Action-specific parameters (class attributes)
    efficiency: float = 0.9  # Budget to capital conversion

    # sometimes an LLM would like to provide this
    description: Optional[str] = None

    @property
    def action_type(self) -> ActionType:
        return ActionType.INVEST_CAPITAL

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.amount or self.amount <= 0:
            return "Capital investment requires positive amount"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        year = str(game_state.current_date.year)
        budget = player.attributes.private_info.budget.get(year, 0.0)
        if budget < self.amount:
            return f"Insufficient budget for capital investment"

        return None

    @classmethod
    def _process_single_action(cls, action: "InvestCapitalAction", player_state: ResearchStrategyPlayerState, game_state: ResearchStrategyGameState) -> str:
        """Process a single capital investment action."""
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < action.amount:
            return f"Fail:Insufficient budget for capital investment of ${action.amount:,.0f}"

        # Invest: convert budget to capital assets
        player_state.private_info.budget[year] = budget - action.amount
        capital_gained = action.amount * action.efficiency
        player_state.private_info.true_asset_balance.capital += capital_gained

        return f"Success:Invested ${action.amount:,.0f} in capital improvements"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all capital investment actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, InvestCapitalAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class SellCapitalAction(Action):
    """Action to sell capital assets for budget."""
    amount: float

    # Action-specific parameters (class attributes)
    efficiency: float = 0.7  # Capital to budget conversion

    @property
    def action_type(self) -> ActionType:
        return ActionType.SELL_CAPITAL

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.amount or self.amount <= 0:
            return "Sell capital requires positive amount"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        if player.attributes.private_info.true_asset_balance.capital < self.amount:
            return f"Insufficient capital to sell"

        return None

    @classmethod
    def _process_single_action(cls, action: "SellCapitalAction", player_state: ResearchStrategyPlayerState, game_state: ResearchStrategyGameState) -> str:
        """Process a single capital sale action."""
        if player_state.private_info.true_asset_balance.capital < action.amount:
            return f"Fail:Insufficient capital to sell ${action.amount:,.0f}"

        # Sell: convert capital to budget
        player_state.private_info.true_asset_balance.capital -= action.amount
        year = str(game_state.current_date.year)
        current_budget = player_state.private_info.budget.get(year, 0.0)
        budget_gained = action.amount * action.efficiency
        player_state.private_info.budget[year] = current_budget + budget_gained

        return f"Success:Sold ${action.amount:,.0f} in capital assets"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all capital sale actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, SellCapitalAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class EspionageAction(Action):
    """Action to conduct espionage on another player."""
    target_player: str
    budget: float
    focus: str  # What information to try to gather

    # Action-specific parameters (class attributes)
    base_success_rate: float = 0.3
    budget_scaling: float = 1000000.0  # Budget per unit of success rate
    max_success_rate: float = 0.8

    @property
    def action_type(self) -> ActionType:
        return ActionType.ESPIONAGE

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.target_player:
            return "Espionage requires target character"

        # Check if target exists
        target_exists = any(p.name == self.target_player for p in players)
        if not target_exists:
            return f"Target character '{self.target_player}' not found"

        if self.budget <= 0:
            return "Espionage requires positive budget"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        year = str(game_state.current_date.year)
        budget = player.attributes.private_info.budget.get(year, 0.0)
        if budget < self.budget:
            return "Insufficient budget for espionage"

        return None

    @classmethod
    def _process_single_action(cls, action: "EspionageAction", player_state: ResearchStrategyPlayerState, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], random_gen: random.Random) -> str:
        """Process a single espionage action."""
        target_player = None
        for p in players:
            if p.name == action.target_player:
                target_player = p
                break

        if not target_player:
            return f"Fail:Espionage target '{action.target_player}' not found"

        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < action.budget:
            return "Fail:Insufficient budget for espionage"

        # Deduct budget
        player_state.private_info.budget[year] = budget - action.budget

        # Store espionage attempt (results processed later)
        success_prob = min(
            action.base_success_rate + (action.budget / action.budget_scaling),
            action.max_success_rate
        )
        success = random_gen.random() < success_prob

        player_state.private_info.espionage.append({
            "target": action.target_player,
            "focus": action.focus,
            "budget": action.budget,
            "success": success,
            "round": game_state.round_number,
        })
        logger.debug(f"Espionage: {player_state.private_info.espionage}")

        return f"{'Success' if success else 'Fail'}:Conducted espionage on {action.target_player}"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all espionage actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, EspionageAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state, players, gamemaster._random)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class PoachTalentAction(Action):
    """Action to poach talent from another player."""
    target: str
    budget: float

    # Action-specific parameters (class attributes)
    base_success_rate: float = 0.2
    budget_scaling: float = 500000.0
    max_success_rate: float = 0.6
    transfer_rate: float = 0.1  # Percentage of target's human resources transferred
    max_transfer: float = 5.0  # Maximum human resources that can be transferred

    @property
    def action_type(self) -> ActionType:
        return ActionType.POACH_TALENT

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.target:
            return "Poaching requires target character"

        if not self.budget or self.budget <= 0:
            return "Poaching requires positive budget"

        target_exists = any(p.name == self.target for p in players)
        if not target_exists:
            return f"Target character '{self.target}' not found"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        year = str(game_state.current_date.year)
        budget = player.attributes.private_info.budget.get(year, 0.0)
        if budget < self.budget:
            return "Insufficient budget for poaching"

        return None

    @classmethod
    def _process_single_action(cls, action: "PoachTalentAction", player_state: ResearchStrategyPlayerState, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], random_gen: random.Random) -> str:
        """Process a single talent poaching action."""
        target_player = None
        for p in players:
            if p.name == action.target:
                target_player = p
                break

        if not target_player:
            return f"Fail:target '{action.target}' not found"

        # Check budget
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < action.budget:
            return "Fail:Insufficient budget for poaching"

        # Deduct budget
        player_state.private_info.budget[year] = budget - action.budget

        # Determine success
        success_prob = min(
            action.base_success_rate + (action.budget / action.budget_scaling),
            action.max_success_rate
        )
        success = random_gen.random() < success_prob

        if success:
            # Transfer some human resources
            transfer_amount = min(
                target_player.attributes.private_info.true_asset_balance.human * action.transfer_rate,
                action.max_transfer
            )
            target_player.attributes.private_info.true_asset_balance.human -= transfer_amount
            player_state.private_info.true_asset_balance.human += transfer_amount
            return f"Success:Poached talent from {action.target} (gained {transfer_amount:.1f} human resources)"
        else:
            return f"Fail:Poaching attempt on {action.target}"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all talent poaching actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, PoachTalentAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state, players, gamemaster._random)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class LobbyAction(Action):
    """Action to lobby for policy changes."""
    message: str
    budget: float

    # Action-specific parameters (class attributes)
    backfire_rate: float = 0.1

    @property
    def action_type(self) -> ActionType:
        return ActionType.LOBBY

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.budget or self.budget <= 0:
            return "Lobbying requires positive budget"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        year = str(game_state.current_date.year)
        budget = player.attributes.private_info.budget.get(year, 0.0)
        if budget < self.budget:
            return "Insufficient budget for lobbying"

        return None

    @classmethod
    def _process_single_action(cls, action: "LobbyAction", player_state: ResearchStrategyPlayerState, game_state: "ResearchStrategyGameState", random_gen: random.Random) -> str:
        """Process a single lobbying action."""
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < action.budget:
            return "Fail:Insufficient budget for lobbying"

        player_state.private_info.budget[year] = budget - action.budget

        # Lobbying may backfire
        if random_gen.random() < action.backfire_rate:
            return f"Fail:Lobbying campaign backfired: {action.message}"
        else:
            return f"Success:Launched lobbying campaign: {action.message}"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all lobbying actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, LobbyAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state, gamemaster._random)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class MarketingAction(Action):
    """Action to launch a marketing campaign."""
    message: str
    budget: float

    @property
    def action_type(self) -> ActionType:
        return ActionType.MARKETING

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.budget or self.budget <= 0:
            return "Marketing requires positive budget"

        player = self._get_player_by_name(self.initiating_character_name, players)
        if not player:
            return f"Player '{self.initiating_character_name}' not found"

        year = str(game_state.current_date.year)
        budget = player.attributes.private_info.budget.get(year, 0.0)
        if budget < self.budget:
            return "Insufficient budget for marketing"

        return None

    @classmethod
    def _process_single_action(cls, action: "MarketingAction", player_state: ResearchStrategyPlayerState, game_state: ResearchStrategyGameState) -> str:
        """Process a single marketing action."""
        year = str(game_state.current_date.year)
        budget = player_state.private_info.budget.get(year, 0.0)
        if budget < action.budget:
            return "Fail:Insufficient budget for marketing"

        player_state.private_info.budget[year] = budget - action.budget
        return f"Success:Launched marketing campaign: {action.message}"

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all marketing actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, MarketingAction):
                continue

            player = action._get_player_by_name(action.initiating_character_name, players)
            if not player:
                continue

            if player.name not in updates:
                updates[player.name] = ResearchStrategyPlayerStateUpdates()

            result = cls._process_single_action(action, player.attributes, game_state)
            updates[player.name].action_results.append(result)

        return updates


@attrs.define
class MessageAction(Action):
    """Action to send a private message to another player."""
    to_character: str
    content: str

    @property
    def action_type(self) -> ActionType:
        return ActionType.MESSAGE

    def validate_action(self, game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Optional[str]:
        error = super().validate_action(game_state, players, gamemaster)
        if error:
            return error

        if not self.to_character:
            return "Message requires recipient"

        target_exists = any(p.name == self.to_character for p in players)
        if not target_exists:
            return f"Recipient '{self.to_character}' not found"

        return None

    @classmethod
    def handle_actions(cls, actions_to_process: list["Action"], game_state: "ResearchStrategyGameState", players: list["ResearchStrategyPlayer"], gamemaster: "ResearchStrategyGameMaster") -> Dict[str, ResearchStrategyPlayerStateUpdates]:
        """Process all message actions."""
        updates = {}
        for action in actions_to_process:
            if not isinstance(action, MessageAction):
                continue

            target_player = action._get_player_by_name(action.to_character, players)
            if not target_player:
                continue

            # Create message
            message = Message(
                from_character=action.initiating_character_name,
                to_character=action.to_character,
                content=action.content,
                timestamp=game_state.current_date,
                round_number=game_state.round_number
            )

            # Add to target player's inbox
            target_player.attributes.add_message(message)

            # Add to updates for recipient
            if target_player.name not in updates:
                updates[target_player.name] = ResearchStrategyPlayerStateUpdates()
            updates[target_player.name].new_messages.append(message)

        return updates


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
class Message:
    """A private message between characters."""
    from_character: str
    to_character: str
    content: str
    timestamp: datetime.datetime
    round_number: int


@attrs.define
class ResearchProject:
    """A research or capital investment project."""
    project_name: str
    description: str
    target_completion_date: datetime.datetime
    # original_budget: float # the budget the project was originally proposed for, for calculating overruns
    committed_budget: float  # per year
    committed_assets: AssetBalance
    status: str = "active"  # active, completed, cancelled
    progress: float = 0.0  # 0.0 to 1.0
    realistic_goals: Optional[str] = None  # Modified by gamemaster if unrealistic


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
