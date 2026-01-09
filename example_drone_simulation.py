"""Example script for running the drone arms control simulation.

Environment Variables:
    OPENAI_API_KEY (required): Your OpenAI API key or API key for compatible provider
    OPENAI_MODEL (optional): Model name to use (default: "gpt-4o-mini")
    OPENAI_API_BASE (optional): Custom API base URL for alternative providers
        Example: "https://api.novita.ai/v3" for Novita AI
        Example: "https://api.together.xyz/v1" for Together AI
    OPENAI_REQUEST_TIMEOUT (optional): Request timeout in seconds (default: 300)
    OPENAI_MAX_RETRIES (optional): Maximum number of retries (default: 3)
    MAX_ROUNDS (optional): Number of simulation rounds to run (default: 3)
    
    Model Info (optional, for custom models):
    OPENAI_MODEL_FAMILY (optional): Model family (default: "chat")
    OPENAI_MODEL_VISION (optional): Supports vision (default: "false")
    OPENAI_MODEL_FUNCTION_CALLING (optional): Supports function calling (default: "true")
    OPENAI_MODEL_JSON_OUTPUT (optional): Supports JSON output (default: "true")
    OPENAI_MODEL_STRUCTURED_OUTPUT (optional): Supports structured output (default: "false")

Example usage with Novita AI:
    export OPENAI_API_KEY="your-novita-key"
    export OPENAI_API_BASE="https://api.novita.ai/v3"
    export OPENAI_MODEL="novita/Novita/Llama-3.1-405B-Instruct-Turbo"
    python example_drone_simulation.py
"""

import os
import sys
from datetime import datetime

# Add the package to path if running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autogen_ext.models.openai import OpenAIChatCompletionClient

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
    
    # Get optional API configuration
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # Use cheaper model by default
    api_base = os.environ.get("OPENAI_API_BASE")  # Optional: for custom providers (e.g., Novita AI)
    request_timeout = int(os.environ.get("OPENAI_REQUEST_TIMEOUT", "300"))  # Default 300 seconds
    max_retries = int(os.environ.get("OPENAI_MAX_RETRIES", "3"))  # Default 3 retries
    
    print(f"Using model: {model_name}")
    if api_base:
        print(f"Using custom API base: {api_base}")
    print(f"Request timeout: {request_timeout}s, Max retries: {max_retries}")
    
    # Initialize LLM client with optional custom API base
    # OpenAIChatCompletionClient from autogen-ext wraps OpenAI's client
    # It accepts 'base_url' for custom API endpoints (OpenAI SDK style)
    client_kwargs = {
        "model": model_name,
        "api_key": api_key,
    }
    
    # Add custom API base if provided (for providers like Novita AI, Together AI, etc.)
    if api_base:
        client_kwargs["base_url"] = api_base
    
    # When using a non-standard model name (custom providers or custom models),
    # autogen-ext requires model_info to describe the model's capabilities
    # Try to determine if we need model_info based on model name
    # Standard OpenAI models like "gpt-4", "gpt-3.5-turbo" don't need it
    standard_openai_models = ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"]
    needs_model_info = not any(model_name.startswith(prefix) for prefix in standard_openai_models)
    
    # If using custom API base, we likely need model_info unless it's a standard model
    # Also try to create without model_info first, and add it if needed
    if needs_model_info or api_base:
        # Provide default model_info for custom models
        # Users can customize via environment variables if needed
        model_info = {
            "family": os.environ.get("OPENAI_MODEL_FAMILY", "chat"),
            "vision": os.environ.get("OPENAI_MODEL_VISION", "false").lower() == "true",
            "function_calling": os.environ.get("OPENAI_MODEL_FUNCTION_CALLING", "true").lower() == "true",
            "json_output": os.environ.get("OPENAI_MODEL_JSON_OUTPUT", "true").lower() == "true",
            "structured_output": os.environ.get("OPENAI_MODEL_STRUCTURED_OUTPUT", "false").lower() == "true",
        }
        client_kwargs["model_info"] = model_info
        print(f"Using model_info for custom model: {model_info}")
    
    # Note: timeout and retries are typically handled by the underlying OpenAI client
    # If you need to customize these, you may need to pass them via client configuration
    # or modify the underlying client initialization. For now, we'll rely on defaults.
    
    try:
        llm_client = OpenAIChatCompletionClient(**client_kwargs)
    except (TypeError, ValueError) as e:
        # Handle case where parameter name might differ or model_info is still needed
        error_str = str(e).lower()
        if api_base and "base_url" in error_str:
            # Try with 'api_base' instead
            if "base_url" in client_kwargs:
                client_kwargs.pop("base_url")
            client_kwargs["api_base"] = api_base
            llm_client = OpenAIChatCompletionClient(**client_kwargs)
        elif "model_info" in error_str and not client_kwargs.get("model_info"):
            # If model_info is still required, add it
            if not client_kwargs.get("model_info"):
                client_kwargs["model_info"] = {
                    "family": "chat",
                    "vision": False,
                    "function_calling": True,
                    "json_output": True,
                    "structured_output": False,
                }
            llm_client = OpenAIChatCompletionClient(**client_kwargs)
        else:
            raise
    
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
    print(f"Running simulation for {max_rounds} rounds")
    
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

