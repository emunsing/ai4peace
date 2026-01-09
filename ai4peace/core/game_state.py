"""Game state management for the simulation platform."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum


class ResourceType(Enum):
    """Types of resources available to characters."""
    TECHNICAL_CAPABILITY = "technical_capability"
    CAPITAL = "capital"  # factories, compute, energy
    HUMAN = "human"  # researchers, engineers, military


@dataclass
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


@dataclass
class PublicView:
    """Public view of a character's information."""
    asset_balance: AssetBalance
    stated_objectives: str
    stated_strategy: str
    public_artifacts: List[str] = field(default_factory=list)


@dataclass
class PrivateInfo:
    """Private information for a character."""
    true_asset_balance: AssetBalance
    objectives: str
    strategy: str
    budget: Dict[str, float]  # budget by year
    projects: List["ResearchProject"] = field(default_factory=list)
    
    def get_current_budget(self, current_date: datetime) -> float:
        """Get budget for the current year."""
        year = current_date.year
        return self.budget.get(str(year), 0.0)


@dataclass
class ResearchProject:
    """A research or capital investment project."""
    name: str
    description: str
    target_completion_date: datetime
    committed_budget: float  # per year
    committed_assets: AssetBalance
    status: str = "active"  # active, completed, cancelled
    progress: float = 0.0  # 0.0 to 1.0
    realistic_goals: Optional[str] = None  # Modified by gamemaster if unrealistic


@dataclass
class Message:
    """A private message between characters."""
    from_character: str
    to_character: str
    content: str
    timestamp: datetime
    round_number: int


@dataclass
class CharacterState:
    """Complete state for a single character."""
    name: str
    private_info: PrivateInfo
    public_view: PublicView
    inbox: List[Message] = field(default_factory=list)
    recent_actions: List[str] = field(default_factory=list)  # Last few rounds
    
    def add_message(self, message: Message):
        """Add a message to the inbox."""
        self.inbox.append(message)
    
    def get_messages_for_round(self, round_number: int) -> List[Message]:
        """Get messages for a specific round."""
        return [msg for msg in self.inbox if msg.round_number == round_number]


@dataclass
class GameState:
    """Complete game state including all characters and public information."""
    current_date: datetime
    round_number: int
    characters: Dict[str, CharacterState]
    public_events: List[str] = field(default_factory=list)
    game_history: List[str] = field(default_factory=list)  # Game master summaries
    
    def get_character(self, name: str) -> Optional[CharacterState]:
        """Get a character by name."""
        return self.characters.get(name)
    
    def add_character(self, character: CharacterState):
        """Add a character to the game."""
        self.characters[character.name] = character
    
    def increment_round(self):
        """Increment to the next round."""
        self.round_number += 1
        # Increment date by some time period (e.g., 3 months per round)
        self.current_date += timedelta(days=90)

