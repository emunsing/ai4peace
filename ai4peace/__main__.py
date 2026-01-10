"""Main entry point for running simulations."""

import os
import sys
from datetime import datetime

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError:
    print("Error: autogen-ext not installed. Install with: pip install autogen-ext[openai]")
    sys.exit(1)

from .core.game_state import GameState
from .core.agent import GameAgent
from .core.gamemaster import GameMaster
from .core.simulation import run_simulation_sync
from .scenarios.drone_arms_control import (
    create_game_state,
    get_game_context,
)


def main():
    """Main entry point."""
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Initialize LLM client
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4")
    llm_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
    )
    
    # Create game state
    print("Initializing game state...")
    game_state = create_game_state(start_date=datetime(2024, 1, 1))
    game_context = get_game_context()
    
    # Create agents
    print("Creating agents...")
    agents = {}
    for character_name, character_state in game_state.characters.items():
        print(f"  Creating agent: {character_name}")
        agent = GameAgent(
            character_name=character_name,
            character_state=character_state,
            llm_client=llm_client,
        )
        agents[character_name] = agent
    
    # Create gamemaster
    print("Creating gamemaster...")
    gamemaster = GameMaster(
        llm_client=llm_client,
        random_seed=42,
    )
    
    # Run simulation
    max_rounds = int(os.environ.get("MAX_ROUNDS", "5"))
    print(f"\nRunning simulation for {max_rounds} rounds...\n")
    
    results = run_simulation_sync(
        game_state=game_state,
        agents=agents,
        gamemaster=gamemaster,
        game_context=game_context,
        max_rounds=max_rounds,
    )
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Rounds completed: {results['rounds_completed']}")
    print(f"Final date: {game_state.current_date.strftime('%Y-%m-%d')}")
    
    # Print final state of each character
    print("\nFinal Character States:")
    for char_name, char_state in game_state.characters.items():
        print(f"\n{char_name}:")
        print(f"  Budget: ${char_state.private_info.get_current_budget(game_state.current_date):,.0f}")
        print(f"  Assets: tech={char_state.private_info.true_asset_balance.technical_capability:.1f}, "
              f"capital={char_state.private_info.true_asset_balance.capital:,.0f}, "
              f"human={char_state.private_info.true_asset_balance.human:.1f}")
        active_projects = [p for p in char_state.private_info.projects if p.status == "active"]
        print(f"  Active Projects: {len(active_projects)}")
        for project in active_projects:
            print(f"    - {project.name}: {project.progress*100:.0f}% complete")


if __name__ == "__main__":
    main()

