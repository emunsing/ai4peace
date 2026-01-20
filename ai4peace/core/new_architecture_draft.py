import abc
import datetime
from abc import ABC, abstractmethod, ABCMeta
datetime

"""
Design philosophy: 
- """

class PlayerState:
    """JSON-serializable representation of a player's state
    This should hold:
    - Current player state
    - Current view of other players' states
    - Any historical state if needed for analysis/logging or reflection
    -
    """

class PlayerStateUpdates:
    """JSON-serializable representation of updates to a player's state.
    The game designer must decide whether these are a diff or a full update to the player state, and design both the
    gamemaster and the player update methods accordingly."""

class GamemasterUpdateMessage:
    "Message from GameMaster to Player with updates on the view of the game state"
    last_action_timestamp: str | int | datetime.datetime
    next_action_timestamp: str | int | datetime.datetime
    state_updates: PlayerStateUpdates

class PlayerProposedMove:
    "Message from Player to GameMaster proposing one round's actions or moves"

class MoveCorrectionMessage:
    "Message from GameMaster to Player correcting or adjusting proposed moves"


class Player(abc.ABC):
    name: str
    player_background: str
    gameplay_description: str
    available_actions: list[str]
    action_history: dict  # Keyed by round timestamp
    last_action_timestamp: str | int | datetime.datetime
    next_action_timestamp: str | int | datetime.datetime
    attributes: PlayerState

    @abstractmethod
    def update_state(self, msg: GamemasterUpdateMessage) -> None:
        # Use game dynamics model to update attributes
        # Call any reflection or reasoning methods
        # Update internal state representation
        # Can update both self.attributes as well as durable memory like action_history and player_background if needed
        pass

    @abstractmethod
    def propose_actions(self) -> PlayerProposedMove:
        pass

    @abstractmethod
    def correct_moves(self, move_modifications: MoveCorrectionMessage) -> PlayerProposedMove:
        pass

class GameState(abc.ABC):
    """JSON-serializable representation of any game state information which is not visible to *any* individual players:
    e.g. slow-moving game processes, consumable chance cards, off-board processes, etc.
    """

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


##### EXAMPLE TEXAS HOLD'EM SCENARIO IMPLEMENTATION BELOW #####

class TexasHoldemGameState(GameState):
    """Game state for Texas Hold'em poker.
    This includes the deck, the community cards, and pot size
    """
    deck: list[str]
    community_cards: list[str]
    pot_size: float

class TexasHoldemPlayerState(PlayerState):
    """Player state for Texas Hold'em poker.
    This includes the player's hand, chips, and view of other players' chips
    """
    hand: list[str]
    chips: float
    current_max_bet_intention: int
    other_players_current_chips: dict[str, float]
    other_players_hand_guesses: dict[str, list[str]]

class TexasHoldemGamemasterUpdateMessage(PlayerStateUpdates):
    """Player state updates for Texas Hold'em poker.
    This includes changes to the player's chips, hand, and view of other players' chips
    """
    chips_change: float
    new_cards: list[str]
    other_players_chips_changes: dict[str, float]

class TexasHoldemPlayerProposedMove(PlayerProposedMove):
    """Player proposed move for Texas Hold'em poker.
    This includes the player's action (fold, call, raise) and amount if applicable
    """
    action: str  # "fold", "call", "raise"
    amount: float | None = None  # Only applicable for "raise"


class TexasHoldemMoveCorrectionMessage(MoveCorrectionMessage):
    """Move correction message for Texas Hold'em poker.
    This includes any adjustments to the player's proposed move
    """
    required_bid_amount: float
    other_player_actions: dict[str, str]  # e.g. {"Player1": "raise", "Player2": "call"}


class TexasHoldemPlayer(Player):
    """Player for Texas Hold'em poker.
    Implements the player logic and decision-making
    """

    def update_state(self, msg: TexasHoldemGamemasterUpdateMessage) -> None:
        pass

    def propose_actions(self) -> TexasHoldemPlayerProposedMove:
        pass

    def correct_moves(self, move_modifications: TexasHoldemMoveCorrectionMessage) -> TexasHoldemPlayerProposedMove:
        pass


class TexasHoldemGameMaster(GenericGameMaster):
    """Game master for Texas Hold'em poker.
    Implements the game logic and player interactions
    Goal: Simulate a full game (multiple hands, until only one player is remaining)
    """

    def create_player_update_messages(self, player: TexasHoldemPlayer) -> TexasHoldemGamemasterUpdateMessage:
        pass

    def get_player_move(self, player: TexasHoldemPlayer) -> TexasHoldemPlayerProposedMove:
        pass

    def simulate_one_round(self, game_state: TexasHoldemGameState, actions: dict[str, TexasHoldemPlayerProposedMove]):
        """
        We have an option of modeling the bidding process within the CorrectionMessage exchange loop, or as separate rounds,
        some of which rounds are bidding-only rounds.
        :param game_state:
        :param actions:
        :return:
        """

    def get_game_ending(self):
        pass

    def run_simulation(self):
        pass