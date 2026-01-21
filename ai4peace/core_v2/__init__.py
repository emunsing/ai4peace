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

from .wargame_state import (
    WargameGameState,
    WargamePlayerState,
    AssetBalance,
    ResearchProject,
    Message,
    PrivateInfo,
    PublicView,
)

from .wargame_actions import (
    WargamePlayerProposedMove,
    WargameMoveCorrectionMessage,
    ActionType,
    ResearchProjectAction,
    EspionageAction,
    MessageAction,
)

from .wargame_updates import (
    WargameGamemasterUpdateMessage,
    WargamePlayerStateUpdates,
)

from .wargame_player import WargamePlayer
from .wargame_gamemaster import WargameGameMaster
from .wargame_scenarios import (
    BasicAIRaceScenario,
    DroneArmsControlScenario,
)

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
    # Wargame state
    "WargameGameState",
    "WargamePlayerState",
    "AssetBalance",
    "ResearchProject",
    "Message",
    "PrivateInfo",
    "PublicView",
    # Wargame actions
    "WargamePlayerProposedMove",
    "WargameMoveCorrectionMessage",
    "ActionType",
    "ResearchProjectAction",
    "EspionageAction",
    "MessageAction",
    # Wargame updates
    "WargameGamemasterUpdateMessage",
    "WargamePlayerStateUpdates",
    # Wargame implementations
    "WargamePlayer",
    "WargameGameMaster",
    # Scenarios
    "BasicAIRaceScenario",
    "DroneArmsControlScenario",
]

