"""Wargame-specific state classes for the generalized game architecture."""

import datetime
from typing import Dict, List, Optional
import attrs

from .new_architecture_draft import GameState, PlayerState


@attrs.define
class AssetBalance:
    """Represents a character's asset balance."""
    technical_capability: float = 0.0
    capital: float = 0.0
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
    projects: List[ResearchProject] = attrs.field(factory=list)
    
    def get_current_budget(self, current_date: datetime.datetime) -> float:
        """Get budget for the current year."""
        year = current_date.year
        return self.budget.get(str(year), 0.0)


@attrs.define
class WargamePlayerState(PlayerState):
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
class WargameGameState(GameState):
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

