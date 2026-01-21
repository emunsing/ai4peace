import abc
import datetime
from abc import abstractmethod
import click
import json
import attrs
import logging
from typing import Optional
from ai4peace.core.simulation_runner import load_scenario_class, create_llm_client

logger = logging.getLogger(__name__)

"""
Design philosophy: 
- Generalized architecture for LLM agents playing multiplayer games
- Game master acts as umpire and state manager
- Players have private information and public views
- JSON-serializable state for logging and replay
"""

@attrs.define
class PlayerState:
    """JSON-serializable representation of a player's state
    This should hold:
    - Current player state
    - Current view of other players' states
    - Any historical state if needed for analysis/logging or reflection
    """
    pass

@attrs.define
class PlayerStateUpdates:
    """JSON-serializable representation of updates to a player's state, as part of a message from the gamemaster to the player.
    The game designer must decide whether these are a diff or a full update to the player state, and design both the
    gamemaster and the player update methods accordingly."""
    pass

@attrs.define
class GamemasterUpdateMessage:
    """Message from GameMaster to Player with updates on the view of the game state"""
    last_action_timestamp: str | int | datetime.datetime
    next_action_timestamp: str | int | datetime.datetime
    state_updates: PlayerStateUpdates

@attrs.define
class PlayerProposedMove:
    """Message from Player to GameMaster proposing one round's actions or moves"""
    pass

@attrs.define
class MoveCorrectionMessage:
    """Message from GameMaster to Player correcting or adjusting proposed moves"""
    pass


class Player(abc.ABC):
    """Abstract base class for game players"""
    
    @abstractmethod
    def update_state(self, msg: GamemasterUpdateMessage) -> None:
        """Use game dynamics model to update attributes
        Call any reflection or reasoning methods
        Update internal state representation
        Can update both self.attributes as well as durable memory like action_history and player_background if needed
        """
        pass

    @abstractmethod
    def propose_actions(self) -> PlayerProposedMove:
        """Propose actions for the current turn"""
        pass

    @abstractmethod
    def correct_moves(self, move_modifications: MoveCorrectionMessage) -> PlayerProposedMove:
        """Correct moves based on gamemaster feedback"""
        pass

@attrs.define
class GameState(abc.ABC):
    """JSON-serializable representation of any game state information which is not visible to *any* individual players:
    e.g. slow-moving game processes, consumable chance cards, off-board processes, etc.
    """
    pass

class GenericGameMaster(abc.ABC):
    players: list[Player]  # The player state is included within these objects
    current_time: str | int | datetime.datetime
    default_timestep: str | int | datetime.timedelta
    current_gamemaster_updates: dict[str, GamemasterUpdateMessage]
    game_state: GameState | None = None

    def get_timestep(self):
        # May implement a custom clock
        return self.default_timestep

    @abstractmethod
    def create_player_update_messages(self, player: Player):
        pass

    @abstractmethod
    def get_player_move(self, player: Player) -> PlayerProposedMove:
        """
        Iterate on a move between the player and gamemaster until the gamemaster accepts the player's move.
        """

    @abstractmethod
    def simulate_one_round(self, game_state, actions):
        """
        Prerequisite: current_gamemaster_updates are not None
        For each player, get their validated proposed move.
        1. Simulate game state progression independent of player actions
        1. Simulate all player actions all player actions to the game state
        1. Update game state
        1. Update player state for each player
        1. Update last- and next-action timestamps using get_timestep()
        1. Create new gamemaster update messages for each player, including any views on the positions of other players
        """
        pass

    @abstractmethod
    def get_game_ending(self):
        pass

    def log_game_update(self):
        pass

    def log_game_state(self):
        pass

    @abstractmethod
    def run_simulation(self):
        """
        Run rounds of game simulation until ending criteria are met
        """
        pass

class GameScenario(abc.ABC):
    """Abstract base class for defining game scenarios.
    Each scenario must implement methods to create the initial game state and players,
    based on parameters passed in through kwargs (e.g. stopping conditions, number of players, etc).
    """

    @abstractmethod
    def create_game_state(self, start_time: str | int | datetime.datetime | None = None) -> GameState:
        pass

    @abstractmethod
    def create_players(self) -> list[Player]:
        pass

    @abstractmethod
    def get_game_master(self) -> GenericGameMaster:
        # Create game state
        # Create players
        # Create gamemaster
        pass
