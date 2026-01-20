import abc
import datetime
from abc import ABC, abstractmethod, ABCMeta
import click
import json
import attrs
from typing import Any
from ai4peace.core.simulation_runner import load_scenario_class
from simulation_runner import  create_llm_client

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

@attrs.define
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
    def get_game_master(self) -> str:
        # Create game state
        # Create players
        # Create gamemaster
        pass


##### EXAMPLE GO FISH SCENARIO IMPLEMENTATION BELOW #####

class GoFishGameState(GameState):
    """Game state for Go Fish
    This is just the deck / draw pile
    """
    draw_pile: list[str]
    current_asking_player: str | None

class GoFishPlayerState(PlayerState):
    """Player state for Go Fish cardgame.
    This includes the player's hand, revealed cards, and a view of other players' chips
    """
    hand: list[str]
    own_revealed_sets: list[list[str]]
    other_players_desired_cards: dict[str, list[str]]
    other_players_missing_cards: dict[str, list[str]]
    other_players_revealed_sets: dict[str, list[str]]

class GoFishGamemasterUpdateMessage(PlayerStateUpdates):
    """Player state updates for Go Fish cardgame.
    This includes changes to the player's hand (additions or removals),
    and changes in cards which have been laid down (self or others)
    The player is then responsible for parsing this into their own state representation.
    """
    new_cards: list[str]
    removed_cards: list[str]
    new_revealed_sets: dict[str, list[str]]


class GoFishPlayerProposedMove(PlayerProposedMove):
    """Player proposed move for Go Fish cardgame.
    This includes the name of the player being asked for a card, and which card is being requested.
    """
    request_card_from_player_name: str
    requested_card: str


class GoFishMoveCorrectionMessage(MoveCorrectionMessage):
    """Move correction message for Go Fish cardgame.
    If the player requested any invalid options, this is a proposed correction
    """
    request_card_from_player_name: str
    requested_card: str


class GoFishPlayer(Player):
    """Player for Go Fish cardgame
    Implements the player logic and decision-making
    """

    def update_state(self, msg: GoFishGamemasterUpdateMessage) -> None:
        pass

    def propose_actions(self) -> GoFishPlayerProposedMove:
        pass

    def correct_moves(self, move_modifications: GoFishMoveCorrectionMessage) -> GoFishPlayerProposedMove:
        # It's very unlikely that in Go fish we would have a bad set of moves, but we need to handle this.
        pass


class GoFishGameMaster(GenericGameMaster):
    """Game master for Go Fish.
    Implements the game logic, player interactions, and end-of-round outlays of collected sets
    Goal: Simulate a full game (until one player has played all of their cards)
    """

    def create_player_update_messages(self, player: GoFishPlayer) -> GoFishGamemasterUpdateMessage:
        pass

    def get_player_move(self, player: GoFishPlayer) -> GoFishPlayerProposedMove:
        pass

    def simulate_one_round(self, game_state: GoFishGameState, actions: dict[str, GoFishPlayerProposedMove]):
        """
        Note: Whoever is asked for a card becomes the "active" player next round
        """

    def get_game_ending(self):
        pass

    def run_simulation(self):
        pass

@attrs.define()
class GoFishScenario(GameScenario):
    llm_client: Any
    n_players: int = 3

    def create_game_state(self, start_time: str | int | datetime.datetime | None = None) -> GoFishGameState:
        pass

    def create_players(self) -> list[GoFishPlayer]:
        pass

    def get_game_master(self) -> str:
        pass


@click.option(
    "--scenario",
    default="ai4peace.core.new_architecture_draft.py:GoFishScenario",
    help="Scenario module path or file path (default: ai4peace.core.new_architecture_draft.py:GoFishScenario)",
)
@click.option(
    "--model",
    default="gpt-4o-mini",
    help="Model name to use (default: gpt-4o-mini)",
)
@click.option(
    "--api-base",
    envvar="OPENAI_API_BASE",
    default=None,
    help="Custom API base URL for alternative providers (or set OPENAI_API_BASE env var)",
)
@click.option(
    "--json-kwargs",
    default=3,
    type=str,
)
def main(
        api_key: str,
        scenario: str,
        model: str,
        api_base: str,
        json_kwargs: str,
):
    """Run a single game simulation.

    This is the main entrypoint for running simulations. It can be called
    from the command line or imported and called programmatically.
    """

    try:
        # Load scenario
        scenario_class = load_scenario_class(scenario)

        llm_client = create_llm_client(
            api_key=api_key,
            model=model,
            api_base=api_base,
        )

        kwargs = json.loads(json_kwargs)

        scenario_instance = scenario_class(llm_client=llm_client, **kwargs)

        gamemaster = scenario_instance.get_game_master()
        gamemaster.run_simulation()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
