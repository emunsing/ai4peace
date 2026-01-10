"""Base scenario class for game scenarios."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from ..core.game_state import GameState, CharacterState


class Scenario(ABC):
    """Base class for game scenarios.
    
    All scenarios must implement the required methods and provide
    the necessary data structures.
    """
    
    def __init__(self):
        """Initialize the scenario with validation."""
        self.validate()
    
    @abstractmethod
    def create_game_state(self, start_date: Optional[datetime] = None) -> GameState:
        """Create initial game state for the scenario.
        
        Args:
            start_date: Optional start date for the game. If None, should use a default.
            
        Returns:
            Initialized GameState object
        """
        pass
    
    @abstractmethod
    def create_characters(self) -> List[CharacterState]:
        """Create all characters for the scenario.
        
        Returns:
            List of CharacterState objects for all characters
        """
        pass
    
    @abstractmethod
    def get_game_context(self) -> str:
        """Get the shared game context description.
        
        Returns:
            String describing the game context, background, and rules
        """
        pass
    
    @abstractmethod
    def get_research_topics(self) -> List[Dict]:
        """Get list of available research topics.
        
        Returns:
            List of dictionaries describing research topics
        """
        pass
    
    def validate(self):
        """Validate that the scenario is properly configured.
        
        Raises:
            ValueError: If scenario configuration is invalid
        """
        # Create a test game state to validate structure
        try:
            game_state = self.create_game_state()
            if not isinstance(game_state, GameState):
                raise ValueError("create_game_state() must return a GameState object")
            
            # Validate characters
            characters = self.create_characters()
            if not isinstance(characters, list) or len(characters) == 0:
                raise ValueError("create_characters() must return a non-empty list")
            
            for char in characters:
                if not isinstance(char, CharacterState):
                    raise ValueError("All characters must be CharacterState objects")
            
            # Validate context
            context = self.get_game_context()
            if not isinstance(context, str) or len(context) == 0:
                raise ValueError("get_game_context() must return a non-empty string")
            
            # Validate research topics
            topics = self.get_research_topics()
            if not isinstance(topics, list):
                raise ValueError("get_research_topics() must return a list")
            
        except Exception as e:
            raise ValueError(f"Scenario validation failed: {e}") from e

