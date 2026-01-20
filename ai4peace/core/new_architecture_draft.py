import abc
import datetime
from abc import ABC, abstractmethod, ABCMeta
import click
import json
import attrs
import random
import logging
import re
from typing import Any, Optional
from ai4peace.core.simulation_runner import load_scenario_class, create_llm_client
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseTextChatMessage

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
    """JSON-serializable representation of updates to a player's state.
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

# Standard deck of cards for Go Fish
CARD_RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
CARD_SUITS = ['♠', '♥', '♦', '♣']

def create_deck() -> list[str]:
    """Create a standard 52-card deck"""
    deck = []
    for rank in CARD_RANKS:
        for suit in CARD_SUITS:
            deck.append(f"{rank}{suit}")
    return deck

def get_rank(card: str) -> str:
    """Extract rank from card string (e.g., 'A♠' -> 'A')"""
    return card.rstrip('♠♥♦♣')

@attrs.define
class GoFishGameState(GameState):
    """Game state for Go Fish
    This is just the deck / draw pile
    """
    draw_pile: list[str] = attrs.field(factory=list)
    current_asking_player: Optional[str] = None

@attrs.define
class GoFishPlayerState(PlayerState):
    """Player state for Go Fish cardgame.
    This includes the player's hand, revealed cards, and a view of other players' revealed sets
    """
    hand: list[str] = attrs.field(factory=list)
    own_revealed_sets: list[list[str]] = attrs.field(factory=list)
    other_players_revealed_sets: dict[str, list[list[str]]] = attrs.field(factory=dict)

@attrs.define
class GoFishPlayerStateUpdates(PlayerStateUpdates):
    """Player state updates for Go Fish cardgame.
    This includes changes to the player's hand (additions or removals),
    and changes in cards which have been laid down (self or others)
    The player is then responsible for parsing this into their own state representation.
    """
    new_cards: list[str] = attrs.field(factory=list)
    removed_cards: list[str] = attrs.field(factory=list)
    new_revealed_sets: dict[str, list[list[str]]] = attrs.field(factory=dict)
    other_players_hand_sizes: dict[str, int] = attrs.field(factory=dict)
    draw_pile_size: int = 0

@attrs.define
class GoFishGamemasterUpdateMessage(GamemasterUpdateMessage):
    """Gamemaster update message for Go Fish"""
    last_action_timestamp: datetime.datetime
    next_action_timestamp: datetime.datetime
    state_updates: GoFishPlayerStateUpdates

@attrs.define
class GoFishPlayerProposedMove(PlayerProposedMove):
    """Player proposed move for Go Fish cardgame.
    This includes the name of the player being asked for a card, and which card is being requested.
    """
    request_card_from_player_name: str = ""
    requested_card: str = ""

@attrs.define
class GoFishMoveCorrectionMessage(MoveCorrectionMessage):
    """Move correction message for Go Fish cardgame.
    If the player requested any invalid options, this is a proposed correction
    """
    request_card_from_player_name: str = ""
    requested_card: str = ""
    error_message: str = ""


@attrs.define
class GoFishPlayer(Player):
    """Player for Go Fish cardgame
    Implements the player logic and decision-making using LLM
    """
    name: str
    llm_client: Any
    attributes: GoFishPlayerState = attrs.field(factory=GoFishPlayerState)
    player_background: str = "You are a strategic Go Fish player."
    gameplay_description: str = "Try to collect sets of 4 cards of the same rank."
    available_actions: list[str] = attrs.field(factory=lambda: ["ask_for_card"])
    action_history: dict = attrs.field(factory=dict)
    last_action_timestamp: datetime.datetime = attrs.field(factory=datetime.datetime.now)
    next_action_timestamp: datetime.datetime = attrs.field(factory=datetime.datetime.now)
    _agent: Optional[AssistantAgent] = None
    
    def __attrs_post_init__(self):
        """Initialize the LLM agent after attributes are set"""
        self.clean_name = re.sub(r"\W|^(?=\d)", "_", self.name)
        system_message = self._build_system_message()
        self._agent = AssistantAgent(
            name=self.clean_name,
            model_client=self.llm_client,
            system_message=system_message,
        )
    
    def _build_system_message(self) -> str:
        """Build the system message for the LLM agent"""
        return f"""You are {self.name}, playing Go Fish.

## Game Rules:
- You have a hand of cards. Your goal is to collect sets of 4 cards of the same rank.
- On your turn, you ask another player for a specific rank (e.g., "A" for Ace, "K" for King).
- If that player has any cards of that rank, they must give you ALL cards of that rank.
- If they don't have that rank, they say "Go Fish" and you draw one card from the deck.
- When you collect 4 cards of the same rank, you lay them down as a set (visible to all players).
- The game ends when someone runs out of cards or the deck is empty.

## Your Strategy:
{self.player_background}
{self.gameplay_description}

## Response Format:
You must respond with a JSON object containing:
{{"request_card_from_player_name": "<player name>", "requested_card": "<rank>"}}

The requested_card should be just the rank (e.g., "A", "2", "3", "J", "Q", "K"), not the full card with suit.
Always respond with valid JSON only, no additional text."""

    def update_state(self, msg: GoFishGamemasterUpdateMessage) -> None:
        """Update player state based on gamemaster message"""
        updates = msg.state_updates
        
        # Update hand
        for card in updates.new_cards:
            if card not in self.attributes.hand:
                self.attributes.hand.append(card)
        for card in updates.removed_cards:
            if card in self.attributes.hand:
                self.attributes.hand.remove(card)
        
        # Update revealed sets
        for player_name, sets in updates.new_revealed_sets.items():
            if player_name == self.name:
                self.attributes.own_revealed_sets = sets
            else:
                self.attributes.other_players_revealed_sets[player_name] = sets
        
        # Update timestamps
        self.last_action_timestamp = msg.last_action_timestamp
        self.next_action_timestamp = msg.next_action_timestamp
        
        # Store in action history
        self.action_history[str(msg.last_action_timestamp)] = {
            "new_cards": updates.new_cards,
            "removed_cards": updates.removed_cards,
            "new_revealed_sets": updates.new_revealed_sets,
        }

    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        try:
            messages = [
                BaseTextChatMessage(source=self.clean_name, content=self._build_system_message()),
                BaseTextChatMessage(source=self.clean_name, content=prompt)
            ]
            response = await self._agent.run(task=messages)
            response_content = response.messages[-1].content if response.messages else ""
            return response_content
        except Exception as e:
            logger.error(f"{self.name} - LLM call failed: {e}", exc_info=True)
            return json.dumps({"request_card_from_player_name": "", "requested_card": ""})

    def propose_actions(self) -> GoFishPlayerProposedMove:
        """Propose actions using LLM"""
        import asyncio
        
        # Build prompt with current state
        prompt = self._build_action_prompt()
        
        # Get LLM response (synchronous wrapper)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        response_text = loop.run_until_complete(self._get_llm_response(prompt))
        
        # Parse response
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)
            
            return GoFishPlayerProposedMove(
                request_card_from_player_name=data.get("request_card_from_player_name", ""),
                requested_card=data.get("requested_card", "")
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"{self.name} - Failed to parse response: {e}")
            return GoFishPlayerProposedMove()

    def _build_action_prompt(self) -> str:
        """Build the prompt for the LLM to decide on actions"""
        hand_ranks = [get_rank(card) for card in self.attributes.hand]
        hand_by_rank = {}
        for rank in hand_ranks:
            hand_by_rank[rank] = hand_by_rank.get(rank, 0) + 1
        
        prompt = f"""## Your Current Hand:
You have {len(self.attributes.hand)} cards in your hand.
Cards by rank: {', '.join([f"{rank} ({count})" for rank, count in sorted(hand_by_rank.items())])}

## Your Revealed Sets:
{len(self.attributes.own_revealed_sets)} sets laid down: {', '.join([f"Set of {get_rank(set_cards[0])}s" for set_cards in self.attributes.own_revealed_sets]) if self.attributes.own_revealed_sets else "None"}

## Other Players' Revealed Sets:
"""
        for player_name, sets in self.attributes.other_players_revealed_sets.items():
            prompt += f"- {player_name}: {len(sets)} sets\n"
        
        prompt += "\n## Your Turn:\n"
        prompt += "Choose a player to ask and a rank to request. "
        prompt += "Think strategically about which ranks you need to complete sets.\n"
        prompt += "Respond with JSON: {\"request_card_from_player_name\": \"<name>\", \"requested_card\": \"<rank>\"}"
        
        return prompt

    def correct_moves(self, move_modifications: GoFishMoveCorrectionMessage) -> GoFishPlayerProposedMove:
        """Correct moves based on gamemaster feedback"""
        logger.info(f"{self.name} - Move corrected: {move_modifications.error_message}")
        # Return the corrected move
        return GoFishPlayerProposedMove(
            request_card_from_player_name=move_modifications.request_card_from_player_name,
            requested_card=move_modifications.requested_card
        )


@attrs.define
class GoFishGameMaster(GenericGameMaster):
    """Game master for Go Fish.
    Implements the game logic, player interactions, and end-of-round outlays of collected sets
    Goal: Simulate a full game (until one player has played all of their cards)
    """
    players: list[GoFishPlayer] = attrs.field(factory=list)
    current_time: datetime.datetime = attrs.field(factory=datetime.datetime.now)
    default_timestep: datetime.timedelta = attrs.field(factory=lambda: datetime.timedelta(seconds=1))
    current_gamemaster_updates: dict[str, GoFishGamemasterUpdateMessage] = attrs.field(factory=dict)
    game_state: GoFishGameState = attrs.field(factory=GoFishGameState)
    round_number: int = 0
    random_seed: Optional[int] = None
    _random: random.Random = attrs.field(init=False)
    
    def __attrs_post_init__(self):
        self._random = random.Random(self.random_seed)

    def get_timestep(self):
        """Get the current timestep"""
        return self.default_timestep

    def create_player_update_messages(self, player: GoFishPlayer) -> GoFishGamemasterUpdateMessage:
        """Create update message for a player"""
        # Get other players' hand sizes (public information)
        other_players_hand_sizes = {}
        for other_player in self.players:
            if other_player.name != player.name:
                other_players_hand_sizes[other_player.name] = len(other_player.attributes.hand)
        
        # Get revealed sets from all players
        all_revealed_sets = {}
        for other_player in self.players:
            all_revealed_sets[other_player.name] = other_player.attributes.own_revealed_sets
        
        # Create the state updates object
        state_updates = GoFishPlayerStateUpdates(
            new_cards=[],
            removed_cards=[],
            new_revealed_sets=all_revealed_sets,
            other_players_hand_sizes=other_players_hand_sizes,
            draw_pile_size=len(self.game_state.draw_pile)
        )
        
        # Create the full update message
        return GoFishGamemasterUpdateMessage(
            last_action_timestamp=self.current_time,
            next_action_timestamp=self.current_time + self.get_timestep(),
            state_updates=state_updates
        )

    def get_player_move(self, player: GoFishPlayer) -> GoFishPlayerProposedMove:
        """Get validated move from player, with correction loop"""
        max_attempts = 5
        for attempt in range(max_attempts):
            move = player.propose_actions()
            
            # Validate move
            validation_error = self._validate_move(player, move)
            if validation_error is None:
                return move
            
            # Create correction message
            correction = GoFishMoveCorrectionMessage(
                request_card_from_player_name=move.request_card_from_player_name,
                requested_card=move.requested_card,
                error_message=validation_error
            )
            
            # Get corrected move
            move = player.correct_moves(correction)
            
            # Validate again
            validation_error = self._validate_move(player, move)
            if validation_error is None:
                return move
            
            logger.warning(f"{player.name} - Invalid move (attempt {attempt + 1}/{max_attempts}): {validation_error}")
        
        # If we get here, return the last move anyway (game will handle it)
        logger.error(f"{player.name} - Failed to get valid move after {max_attempts} attempts")
        return move

    def _validate_move(self, player: GoFishPlayer, move: GoFishPlayerProposedMove) -> Optional[str]:
        """Validate a player's move. Returns error message if invalid, None if valid."""
        # Check if player has cards in hand
        if not player.attributes.hand:
            return "You have no cards in your hand"
        
        # Check if target player exists
        target_player = None
        for p in self.players:
            if p.name == move.request_card_from_player_name:
                target_player = p
                break
        
        if target_player is None:
            return f"Player '{move.request_card_from_player_name}' does not exist"
        
        if target_player.name == player.name:
            return "You cannot ask yourself for a card"
        
        # Check if target player has cards
        if not target_player.attributes.hand:
            return f"{target_player.name} has no cards in their hand"
        
        # Check if requested card rank is valid
        if not move.requested_card or move.requested_card not in CARD_RANKS:
            return f"Invalid card rank: {move.requested_card}. Must be one of {CARD_RANKS}"
        
        # Check if player has at least one card of the requested rank (optional rule - some variants allow this)
        # For now, we'll allow asking for any rank
        
        return None  # Valid move

    def simulate_one_round(self, game_state: GoFishGameState, actions: dict[str, GoFishPlayerProposedMove]):
        """Simulate one round of Go Fish"""
        # Get the current asking player
        asking_player_name = game_state.current_asking_player
        if asking_player_name is None:
            # First round - pick random player
            asking_player = self._random.choice(self.players)
            asking_player_name = asking_player.name
            game_state.current_asking_player = asking_player_name
        
        # Find the asking player
        asking_player = None
        for p in self.players:
            if p.name == asking_player_name:
                asking_player = p
                break
        
        if asking_player is None:
            logger.error(f"Could not find asking player: {asking_player_name}")
            return
        
        # Get the move for this player
        move = actions.get(asking_player_name)
        if move is None:
            logger.error(f"No move found for {asking_player_name}")
            return
        
        # Find the target player
        target_player = None
        for p in self.players:
            if p.name == move.request_card_from_player_name:
                target_player = p
                break
        
        if target_player is None:
            logger.error(f"Target player not found: {move.request_card_from_player_name}")
            return
        
        requested_rank = move.requested_card
        
        # Track card changes for update messages
        asking_player_new_cards = []
        asking_player_removed_cards = []
        target_player_removed_cards = []
        
        # Check if target player has cards of that rank
        matching_cards = [card for card in target_player.attributes.hand if get_rank(card) == requested_rank]
        
        if matching_cards:
            # Target player has the cards - transfer them
            logger.info(f"{asking_player_name} asked {target_player.name} for {requested_rank}. {target_player.name} had {len(matching_cards)} card(s).")
            
            # Remove cards from target player
            for card in matching_cards:
                target_player.attributes.hand.remove(card)
                target_player_removed_cards.append(card)
            
            # Add cards to asking player
            asking_player.attributes.hand.extend(matching_cards)
            asking_player_new_cards.extend(matching_cards)
            
            # Check if asking player now has a set of 4
            asking_player_rank_counts = {}
            for card in asking_player.attributes.hand:
                rank = get_rank(card)
                asking_player_rank_counts[rank] = asking_player_rank_counts.get(rank, 0) + 1
            
            # Find and remove sets of 4
            for rank, count in asking_player_rank_counts.items():
                if count >= 4:
                    set_cards = [card for card in asking_player.attributes.hand if get_rank(card) == rank][:4]
                    for card in set_cards:
                        asking_player.attributes.hand.remove(card)
                        asking_player_removed_cards.append(card)
                    asking_player.attributes.own_revealed_sets.append(set_cards)
                    logger.info(f"{asking_player_name} collected a set of {rank}s!")
            
            # Asking player gets another turn
            game_state.current_asking_player = asking_player_name
            
        else:
            # Target player doesn't have the cards - Go Fish!
            logger.info(f"{asking_player_name} asked {target_player.name} for {requested_rank}. Go Fish!")
            
            if game_state.draw_pile:
                # Draw a card
                drawn_card = game_state.draw_pile.pop()
                asking_player.attributes.hand.append(drawn_card)
                asking_player_new_cards.append(drawn_card)
                logger.info(f"{asking_player_name} drew {drawn_card}")
                
                # Check if asking player now has a set of 4
                asking_player_rank_counts = {}
                for card in asking_player.attributes.hand:
                    rank = get_rank(card)
                    asking_player_rank_counts[rank] = asking_player_rank_counts.get(rank, 0) + 1
                
                # Find and remove sets of 4
                for rank, count in asking_player_rank_counts.items():
                    if count >= 4:
                        set_cards = [card for card in asking_player.attributes.hand if get_rank(card) == rank][:4]
                        for card in set_cards:
                            asking_player.attributes.hand.remove(card)
                            asking_player_removed_cards.append(card)
                        asking_player.attributes.own_revealed_sets.append(set_cards)
                        logger.info(f"{asking_player_name} collected a set of {rank}s!")
            else:
                logger.info("Draw pile is empty!")
            
            # Next player's turn (cycle to next player)
            current_index = next((i for i, p in enumerate(self.players) if p.name == asking_player_name), 0)
            next_index = (current_index + 1) % len(self.players)
            game_state.current_asking_player = self.players[next_index].name
        
        # Create update messages for all players with the changes
        for player in self.players:
            # Get all revealed sets
            all_revealed_sets = {}
            for p in self.players:
                all_revealed_sets[p.name] = p.attributes.own_revealed_sets
            
            # Determine what changed for this player
            if player.name == asking_player_name:
                new_cards = asking_player_new_cards
                removed_cards = asking_player_removed_cards
            elif player.name == target_player.name:
                new_cards = []
                removed_cards = target_player_removed_cards
            else:
                new_cards = []
                removed_cards = []
            
            # Get other players' hand sizes
            other_players_hand_sizes = {}
            for p in self.players:
                if p.name != player.name:
                    other_players_hand_sizes[p.name] = len(p.attributes.hand)
            
            # Create update message
            state_updates = GoFishPlayerStateUpdates(
                new_cards=new_cards,
                removed_cards=removed_cards,
                new_revealed_sets=all_revealed_sets,
                other_players_hand_sizes=other_players_hand_sizes,
                draw_pile_size=len(game_state.draw_pile)
            )
            
            update_msg = GoFishGamemasterUpdateMessage(
                last_action_timestamp=self.current_time,
                next_action_timestamp=self.current_time + self.get_timestep(),
                state_updates=state_updates
            )
            
            self.current_gamemaster_updates[player.name] = update_msg
        
        # Update timestamps
        self.current_time += self.get_timestep()
        self.round_number += 1

    def get_game_ending(self) -> Optional[str]:
        """Check if game is over. Returns winner name if game is over, None otherwise."""
        # Game ends if:
        # 1. A player has no cards left in hand (and no cards in draw pile to draw)
        # 2. Draw pile is empty and no one can make a move
        
        # Check if any player has no cards
        for player in self.players:
            if not player.attributes.hand:
                # Count total sets
                total_sets = {}
                for p in self.players:
                    total_sets[p.name] = len(p.attributes.own_revealed_sets)
                
                # Find player with most sets
                winner = max(self.players, key=lambda p: len(p.attributes.own_revealed_sets))
                return winner.name
        
        # Check if draw pile is empty and game is stuck
        if not self.game_state.draw_pile:
            # Check if all players have cards (game can continue)
            all_have_cards = all(len(p.attributes.hand) > 0 for p in self.players)
            if all_have_cards:
                return None  # Game continues
            
            # If draw pile is empty and someone has no cards, game should have ended above
            # If we get here, find winner by sets
            winner = max(self.players, key=lambda p: len(p.attributes.own_revealed_sets))
            return winner.name
        
        return None  # Game continues

    def run_simulation(self):
        """Run the full simulation"""
        logger.info("Starting Go Fish simulation")
        logger.info(f"Players: {[p.name for p in self.players]}")
        logger.info(f"Draw pile size: {len(self.game_state.draw_pile)}")
        
        # Initial update messages for all players
        for player in self.players:
            update_msg = self.create_player_update_messages(player)
            player.update_state(update_msg)
            self.current_gamemaster_updates[player.name] = update_msg
        
        max_rounds = 1000  # Safety limit
        round_count = 0
        
        while round_count < max_rounds:
            round_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Round {round_count}")
            logger.info(f"{'='*60}")
            
            # Get moves from all players (but only the current asking player will act)
            actions = {}
            asking_player_name = self.game_state.current_asking_player
            if asking_player_name:
                asking_player = next((p for p in self.players if p.name == asking_player_name), None)
                if asking_player:
                    move = self.get_player_move(asking_player)
                    actions[asking_player_name] = move
            
            # Simulate the round (this will create update messages and update player states)
            self.simulate_one_round(self.game_state, actions)
            
            # Update all players with the new state
            for player in self.players:
                if player.name in self.current_gamemaster_updates:
                    player.update_state(self.current_gamemaster_updates[player.name])
            
            # Log current state
            self.log_game_state()
            
            # Check for game ending
            winner = self.get_game_ending()
            if winner:
                logger.info(f"\n{'='*60}")
                logger.info(f"Game Over! Winner: {winner}")
                logger.info(f"{'='*60}")
                
                # Log final scores
                for player in self.players:
                    logger.info(f"{player.name}: {len(player.attributes.own_revealed_sets)} sets, {len(player.attributes.hand)} cards in hand")
                break
        
        if round_count >= max_rounds:
            logger.warning(f"Game reached maximum rounds ({max_rounds})")

    def log_game_state(self):
        """Log current game state"""
        logger.info(f"Draw pile: {len(self.game_state.draw_pile)} cards")
        logger.info(f"Current asking player: {self.game_state.current_asking_player}")
        for player in self.players:
            logger.info(f"{player.name}: {len(player.attributes.hand)} cards in hand, {len(player.attributes.own_revealed_sets)} sets")

@attrs.define()
class GoFishScenario(GameScenario):
    llm_client: Any
    n_players: int = 3
    random_seed: Optional[int] = None

    def create_game_state(self, start_time: str | int | datetime.datetime | None = None) -> GoFishGameState:
        """Create initial game state with shuffled deck"""
        deck = create_deck()
        random_gen = random.Random(self.random_seed)
        random_gen.shuffle(deck)
        
        return GoFishGameState(
            draw_pile=deck,
            current_asking_player=None
        )

    def create_players(self) -> list[GoFishPlayer]:
        """Create players and deal initial hands"""
        players = []
        player_names = [f"Player{i+1}" for i in range(self.n_players)]
        
        # Create players
        for name in player_names:
            player = GoFishPlayer(
                name=name,
                llm_client=self.llm_client,
                attributes=GoFishPlayerState(),
                player_background=f"You are {name}, a strategic Go Fish player. Try to collect sets of 4 cards of the same rank.",
                gameplay_description="Pay attention to what other players ask for and what sets they reveal to deduce what cards they might have."
            )
            players.append(player)
        
        return players

    def get_game_master(self) -> GoFishGameMaster:
        """Create and initialize the game master"""
        # Create game state
        game_state = self.create_game_state()
        
        # Create players
        players = self.create_players()
        
        # Deal initial hands
        cards_per_player = 7 if self.n_players <= 2 else 5
        random_gen = random.Random(self.random_seed)
        
        for i, player in enumerate(players):
            # Deal cards to this player
            for _ in range(cards_per_player):
                if game_state.draw_pile:
                    card = game_state.draw_pile.pop()
                    player.attributes.hand.append(card)
        
        # Check for initial sets (4 of a kind in initial hand)
        for player in players:
            rank_counts = {}
            for card in player.attributes.hand:
                rank = get_rank(card)
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
            # Remove sets of 4
            for rank, count in rank_counts.items():
                if count >= 4:
                    set_cards = [card for card in player.attributes.hand if get_rank(card) == rank][:4]
                    for card in set_cards:
                        player.attributes.hand.remove(card)
                    player.attributes.own_revealed_sets.append(set_cards)
                    logger.info(f"{player.name} started with a set of {rank}s!")
        
        # Set initial asking player (random)
        if players:
            initial_player = random_gen.choice(players)
            game_state.current_asking_player = initial_player.name
        
        # Create gamemaster
        gamemaster = GoFishGameMaster(
            players=players,
            current_time=datetime.datetime.now(),
            default_timestep=datetime.timedelta(seconds=1),
            current_gamemaster_updates={},
            game_state=game_state,
            round_number=0,
            random_seed=self.random_seed
        )
        
        return gamemaster


@click.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    required=True,
    help="OpenAI API key (or set OPENAI_API_KEY env var)",
)
@click.option(
    "--scenario",
    default="ai4peace.core.new_architecture_draft:GoFishScenario",
    help="Scenario module path or file path (default: ai4peace.core.new_architecture_draft:GoFishScenario)",
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
    default='{"n_players": 3}',
    type=str,
    help='JSON string with scenario parameters (default: \'{"n_players": 3}\')',
)
def main(
        api_key: str,
        scenario: str,
        model: str,
        api_base: Optional[str],
        json_kwargs: str,
):
    """Run a single game simulation.

    This is the main entrypoint for running simulations. It can be called
    from the command line or imported and called programmatically.
    
    Example:
        python -m ai4peace.core.new_architecture_draft --api-key $OPENAI_API_KEY --json-kwargs '{"n_players": 3, "random_seed": 42}'
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

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


if __name__ == "__main__":
    main()
