"""Action system for agent decisions."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


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


@dataclass
class ResearchProjectAction:
    """Details for creating a research project."""
    name: str
    description: str
    target_completion_date: str  # ISO format date
    annual_budget: float
    required_assets: Dict[str, float]  # technical_capability, capital, human


@dataclass
class EspionageAction:
    """Details for espionage action."""
    target_character: str
    budget: float
    focus: str  # What information to try to gather


@dataclass
class MessageAction:
    """Details for sending a private message."""
    to_character: str
    content: str


@dataclass
class Action:
    """An action taken by an agent."""
    action_type: ActionType
    character_name: str
    round_number: int
    
    # Action-specific data
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for serialization."""
        result = {
            "action_type": self.action_type.value,
            "character_name": self.character_name,
            "round_number": self.round_number,
        }
        
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

