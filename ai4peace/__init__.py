"""AI4Peace: Strategic Multi-Agent Simulation Platform for International Technology Policy."""

__version__ = "0.1.0"

# Export main components
from .core import (
    GameState,
    CharacterState,
    AssetBalance,
    ResearchProject,
    GameAgent,
    GameMaster,
    Simulation,
    run_simulation_sync,
    Action,
    ActionType,
)

from .scenarios import (
    create_game_state as create_drone_game_state,
    get_game_context as get_drone_game_context,
    get_research_topics,
)

__all__ = [
    # Core components
    "GameState",
    "CharacterState",
    "AssetBalance",
    "ResearchProject",
    "GameAgent",
    "GameMaster",
    "Simulation",
    "run_simulation_sync",
    "Action",
    "ActionType",
    # Scenario utilities
    "create_drone_game_state",
    "get_drone_game_context",
    "get_research_topics",
]

