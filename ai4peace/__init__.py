"""Core v2 architecture for generalized multiplayer game simulations."""

from .new_architecture_draft import (
    Player,
    GenericGameMaster,
    GameScenario,
    GameState,
    PlayerState,
    PlayerStateUpdates,
    GamemasterUpdateMessage,
    PlayerProposedMove,
    MoveCorrectionMessage,
)

from .research_strategy_game_mechanics import (ResearchStrategyGameMaster,
                                               ResearchStrategyGameState,
                                               ResearchStrategyPlayerState,
                                               AssetBalance,
                                               ResearchProject,
                                               Message,
                                               PrivateInfo,
                                               PublicView,
                                               ResearchStrategyPlayer,
                                               ResearchStrategyGamemasterUpdateMessage,
                                               ResearchStrategyPlayerStateUpdates,
                                               ActionType,
                                               EspionageAction,
                                               MessageAction,
                                               )

from .research_strategy_scenario_drones import DroneArmsControlScenario
from .research_strategy_scenario_basic_ai_race import BasicAIRaceScenario

__all__ = [
    # Base architecture
    "Player",
    "GenericGameMaster",
    "GameScenario",
    "GameState",
    "PlayerState",
    "PlayerStateUpdates",
    "GamemasterUpdateMessage",
    "PlayerProposedMove",
    "MoveCorrectionMessage",
    # ResearchStrategy state
    "ResearchStrategyGameState",
    "ResearchStrategyPlayerState",
    "AssetBalance",
    "ResearchProject",
    "Message",
    "PrivateInfo",
    "PublicView",
    # ResearchStrategy actions
    "ResearchStrategyPlayerProposedMove",
    "ResearchStrategyMoveCorrectionMessage",
    "ActionType",
    "ResearchProjectAction",
    "EspionageAction",
    "MessageAction",
    # ResearchStrategy updates
    "ResearchStrategyGamemasterUpdateMessage",
    "ResearchStrategyPlayerStateUpdates",
    # ResearchStrategy implementations
    "ResearchStrategyPlayer",
    "ResearchStrategyGameMaster",
    # Scenarios
    "BasicAIRaceScenario",
    "DroneArmsControlScenario",
]

