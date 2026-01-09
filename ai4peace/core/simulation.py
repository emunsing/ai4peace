"""Main simulation runner for the game."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from .game_state import GameState
from .agent import GameAgent
from .gamemaster import GameMaster
from .actions import Action


class Simulation:
    """Main simulation orchestrator."""
    
    def __init__(
        self,
        game_state: GameState,
        agents: Dict[str, GameAgent],
        gamemaster: GameMaster,
        game_context: str,
        max_rounds: int = 10,
    ):
        """Initialize simulation.
        
        Args:
            game_state: Initial game state
            agents: Dictionary mapping character names to GameAgent instances
            gamemaster: GameMaster instance
            game_context: Shared context description for all agents
            max_rounds: Maximum number of rounds to simulate
        """
        self.game_state = game_state
        self.agents = agents
        self.gamemaster = gamemaster
        self.game_context = game_context
        self.max_rounds = max_rounds
        self.history: List[Dict] = []
    
    async def run(self) -> Dict:
        """Run the simulation.
        
        Returns:
            Dictionary containing simulation results and history
        """
        print(f"Starting simulation: {len(self.agents)} agents, {self.max_rounds} rounds")
        print(f"Initial date: {self.game_state.current_date.strftime('%Y-%m-%d')}\n")
        
        for round_num in range(1, self.max_rounds + 1):
            print(f"\n{'='*60}")
            print(f"ROUND {round_num} ({self.game_state.current_date.strftime('%Y-%m-%d')})")
            print(f"{'='*60}\n")
            
            # Get action summary from previous round (or initial state)
            action_summary = self._get_action_summary()
            
            # Each agent takes their turn
            actions: List[Action] = []
            for character_name, agent in self.agents.items():
                print(f"\n--- {character_name} is deciding actions ---")
                
                # Get private updates for this character
                private_updates = self._get_private_updates(character_name)
                
                try:
                    action = await agent.take_turn(
                        game_state=self.game_state,
                        game_context=self.game_context,
                        action_summary=action_summary,
                        private_updates=private_updates,
                    )
                    actions.append(action)
                    print(f"{character_name} submitted action: {action.action_type.value}")
                except Exception as e:
                    print(f"Error getting action from {character_name}: {e}")
                    # Create a no-op action
                    from .actions import Action, ActionType
                    actions.append(Action(
                        action_type=ActionType.MARKETING,  # Dummy
                        character_name=character_name,
                        round_number=round_num,
                    ))
            
            # Gamemaster processes all actions
            print(f"\n--- GameMaster processing round ---")
            private_summaries = self.gamemaster.process_round(
                game_state=self.game_state,
                actions=actions,
            )
            
            # Store round history
            round_history = {
                "round": round_num,
                "date": self.game_state.current_date.isoformat(),
                "actions": [a.to_dict() for a in actions],
                "global_summary": self.game_state.game_history[-1] if self.game_state.game_history else "",
                "private_summaries": private_summaries,
            }
            self.history.append(round_history)
            
            # Display summary
            print(f"\nRound {round_num} Summary:")
            print(self.game_state.game_history[-1] if self.game_state.game_history else "No summary")
        
        print(f"\n{'='*60}")
        print("SIMULATION COMPLETE")
        print(f"{'='*60}\n")
        
        return {
            "final_state": self.game_state,
            "history": self.history,
            "rounds_completed": self.max_rounds,
        }
    
    def _get_action_summary(self) -> str:
        """Get summary of actions from previous rounds."""
        if not self.game_state.game_history:
            return "This is the first round. No previous actions to summarize."
        
        # Get last few summaries
        recent_summaries = self.game_state.game_history[-3:]
        return "\n\n".join(recent_summaries)
    
    def _get_private_updates(self, character_name: str) -> str:
        """Get private updates for a character.
        
        This will be populated by the gamemaster after processing.
        For now, we'll use a placeholder that gets updated.
        """
        # Check if character has stored private updates
        character = self.game_state.get_character(character_name)
        if character and hasattr(character, '_private_updates'):
            updates = character._private_updates
            if updates:
                return "\n".join(updates)
        
        return "No private updates available yet."


def run_simulation_sync(
    game_state: GameState,
    agents: Dict[str, GameAgent],
    gamemaster: GameMaster,
    game_context: str,
    max_rounds: int = 10,
) -> Dict:
    """Synchronous wrapper for running simulation."""
    simulation = Simulation(
        game_state=game_state,
        agents=agents,
        gamemaster=gamemaster,
        game_context=game_context,
        max_rounds=max_rounds,
    )
    return asyncio.run(simulation.run())

