"""Example script for running the drone arms control simulation."""

import os
import sys
from datetime import datetime

# Add the package to path if running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError:
    print("Error: autogen-ext not installed.")
    print("Install with: pip install autogen-ext[openai]")
    sys.exit(1)

from ai4peace.core.game_state import GameState
from ai4peace.core.agent import GameAgent
from ai4peace.core.gamemaster import GameMaster
from ai4peace.core.simulation import run_simulation_sync
from ai4peace.scenarios.drone_arms_control import (
    create_game_state,
    get_game_context,
)


def main():
    """Run the drone arms control simulation."""
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    # Initialize LLM client
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # Use cheaper model by default
    print(f"Using model: {model_name}")
    
    llm_client = OpenAIChatCompletionClient(
        model=model_name,
        api_key=api_key,
    )
    
    # Create game state
    print("\n" + "="*60)
    print("Initializing Drone Arms Control Simulation")
    print("="*60)
    print("\nCreating game state...")
    game_state = create_game_state(start_date=datetime(2024, 1, 1))
    game_context = get_game_context()
    
    # Create agents
    print("Creating agents...")
    agents = {}
    for character_name, character_state in game_state.characters.items():
        print(f"  - {character_name}")
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
    
    # Get number of rounds
    max_rounds = int(os.environ.get("MAX_ROUNDS", "3"))
    print(f"\n{'='*60}")
    print(f"Running simulation for {max_rounds} rounds")
    print(f"{'='*60}\n")
    
    # Run simulation
    try:
        results = run_simulation_sync(
            game_state=game_state,
            agents=agents,
            gamemaster=gamemaster,
            game_context=game_context,
            max_rounds=max_rounds,
        )
        
        # Print final results
        print("\n" + "="*60)
        print("SIMULATION COMPLETE - FINAL RESULTS")
        print("="*60)
        print(f"\nRounds completed: {results['rounds_completed']}")
        print(f"Final date: {game_state.current_date.strftime('%Y-%m-%d')}")
        
        # Print final state of each character
        print("\n" + "-"*60)
        print("Final Character States")
        print("-"*60)
        for char_name, char_state in game_state.characters.items():
            print(f"\n{char_name}:")
            budget = char_state.private_info.get_current_budget(game_state.current_date)
            print(f"  Budget: ${budget:,.0f}")
            assets = char_state.private_info.true_asset_balance
            print(f"  Assets:")
            print(f"    - Technical Capability: {assets.technical_capability:.1f}")
            print(f"    - Capital: ${assets.capital:,.0f}")
            print(f"    - Human Resources: {assets.human:.1f}")
            
            active_projects = [p for p in char_state.private_info.projects if p.status == "active"]
            completed_projects = [p for p in char_state.private_info.projects if p.status == "completed"]
            
            print(f"  Active Projects: {len(active_projects)}")
            for project in active_projects:
                print(f"    - {project.name}: {project.progress*100:.0f}% complete")
            
            if completed_projects:
                print(f"  Completed Projects: {len(completed_projects)}")
                for project in completed_projects:
                    print(f"    - {project.name}")
        
        print("\n" + "="*60)
        print("Simulation complete!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during simulation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

