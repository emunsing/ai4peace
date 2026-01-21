"""Core simulation runner functionality."""

import logging
import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any

try:
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError:
    OpenAIChatCompletionClient = None

from .game_state import GameState
from .agent import GameAgent
from .gamemaster import GameMaster
from .simulation import run_simulation_sync
from .utils import print_character_states
from ..scenarios.base import Scenario

logger = logging.getLogger(__name__)


class ModelFamily(str, Enum):
    """Valid model families for autogen-ext."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"

def load_scenario(scenario_path: str) -> Scenario:
    cls = load_scenario_class(scenario_path)
    return cls()

def load_scenario_class(scenario_path: str, must_subclass=Scenario):
    """Load a scenario from a Python file.
    
    Args:
        scenario_path: Path to the scenario file (Python module path, file path, 
                       or "module:ClassName" format)
        
    Returns:
        Scenario instance
        
    Raises:
        ImportError: If scenario cannot be loaded
        ValueError: If scenario is invalid
    """
    # Handle "module:ClassName" format (e.g., "ai4peace.scenarios.drone_arms_control:DroneArmsControlScenario")
    if ":" in scenario_path:
        module_path, class_name = scenario_path.rsplit(":", 1)
        try:
            from importlib import import_module
            module = import_module(module_path)
            scenario_class = getattr(module, class_name)
            if isinstance(scenario_class, type) and issubclass(scenario_class, must_subclass):
                logger.info(f"Loaded scenario class: {class_name} from {module_path}")
                return scenario_class
            else:
                raise ValueError(f"{class_name} is not a {must_subclass.__name__} subclass")
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not load scenario class {class_name} from {module_path}: {e}")
    
    # Try as module path (e.g., "ai4peace.scenarios.drone_arms_control")
    try:
        from importlib import import_module
        module = import_module(scenario_path)
        # Look for a Scenario subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Scenario) and 
                attr is not Scenario):
                logger.info(f"Loaded scenario class: {attr_name} from {scenario_path}")
                return attr
    except ImportError:
        pass
    
    # Try as file path (e.g., "scenarios/drone_arms_control.py")
    if os.path.exists(scenario_path):
        # Add directory to path
        scenario_dir = str(Path(scenario_path).parent.absolute())
        if scenario_dir not in sys.path:
            sys.path.insert(0, scenario_dir)
        
        # Import the module
        module_name = Path(scenario_path).stem
        try:
            from importlib import import_module
            module = import_module(module_name)
            # Look for a Scenario subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Scenario) and 
                    attr is not Scenario):
                    logger.info(f"Loaded scenario class: {attr_name} from {scenario_path}")
                    return attr
        except ImportError as e:
            raise ImportError(f"Could not import scenario from {scenario_path}: {e}")
    
    raise ValueError(f"No Scenario subclass found in {scenario_path}")


def create_llm_client(
    api_key: str,
    model: str = "gpt-4o-mini",
    api_base: Optional[str] = None,
    family: str = "chat",
    vision: bool = False,
    function_calling: bool = True,
    json_output: bool = True,
    structured_output: bool = False,
) -> Any:
    """Create an LLM client with the specified configuration.
    
    Args:
        api_key: API key for the LLM provider
        model: Model name to use
        api_base: Optional custom API base URL
        family: Model family (must be from ModelFamily enum)
        vision: Whether model supports vision
        function_calling: Whether model supports function calling
        json_output: Whether model supports JSON output
        structured_output: Whether model supports structured output
        
    Returns:
        OpenAIChatCompletionClient instance
    """
    if OpenAIChatCompletionClient is None:
        raise ImportError("autogen-ext not installed. Install with: pip install autogen-ext[openai]")
    
    # Validate family
    if family not in [f.value for f in ModelFamily]:
        raise ValueError(f"family must be one of {[f.value for f in ModelFamily]}, got {family}")
    
    client_kwargs = {
        "model": model,
        "api_key": api_key,
    }
    
    if api_base:
        client_kwargs["base_url"] = api_base
    
    # Determine if model_info is needed
    standard_openai_models = ["gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"]
    needs_model_info = not any(model.startswith(prefix) for prefix in standard_openai_models)
    
    if needs_model_info or api_base:
        model_info = {
            "family": family,
            "vision": vision,
            "function_calling": function_calling,
            "json_output": json_output,
            "structured_output": structured_output,
        }
        client_kwargs["model_info"] = model_info
        logger.debug(f"Using model_info: {model_info}")
    
    try:
        return OpenAIChatCompletionClient(**client_kwargs)
    except (TypeError, ValueError) as e:
        # Handle case where parameter name might differ
        error_str = str(e).lower()
        if api_base and "base_url" in error_str:
            if "base_url" in client_kwargs:
                client_kwargs.pop("base_url")
            client_kwargs["api_base"] = api_base
            return OpenAIChatCompletionClient(**client_kwargs)
        elif "model_info" in error_str and not client_kwargs.get("model_info"):
            client_kwargs["model_info"] = {
                "family": family,
                "vision": vision,
                "function_calling": function_calling,
                "json_output": json_output,
                "structured_output": structured_output,
            }
            return OpenAIChatCompletionClient(**client_kwargs)
        else:
            raise


def simulate_one_game(
    api_key: str,
    scenario: Scenario,
    model: str = "gpt-4o-mini",
    api_base: Optional[str] = None,
    max_rounds: int = 3,
    random_seed: Optional[int] = None,
    start_date: Optional[datetime] = None,
    family: str = "chat",
    vision: bool = False,
    function_calling: bool = True,
    json_output: bool = True,
    structured_output: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run a single game simulation.
    
    Args:
        api_key: API key for the LLM provider
        scenario: Scenario instance to use
        model: Model name to use
        api_base: Optional custom API base URL
        max_rounds: Number of rounds to simulate
        random_seed: Optional random seed for reproducibility
        start_date: Optional start date for the game
        family: Model family (default: "chat")
        vision: Whether model supports vision (default: False)
        function_calling: Whether model supports function calling (default: True)
        json_output: Whether model supports JSON output (default: True)
        structured_output: Whether model supports structured output (default: False)
        verbose: Whether to enable verbose logging (default: False)
        
    Returns:
        Dictionary containing simulation results:
        - "final_state": Final GameState
        - "history": List of round histories
        - "rounds_completed": Number of rounds completed
    """
    # Set up logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting simulation: {max_rounds} rounds")
    if api_base:
        logger.info(f"Using custom API base: {api_base}")
    logger.debug(f"Model: {model}, Family: {family}")
    
    # Create LLM client
    llm_client = create_llm_client(
        api_key=api_key,
        model=model,
        api_base=api_base,
        family=family,
        vision=vision,
        function_calling=function_calling,
        json_output=json_output,
        structured_output=structured_output,
    )
    
    # Create game state
    logger.info("Creating game state...")
    game_state = scenario.create_game_state(start_date=start_date or datetime(2024, 1, 1))
    game_context = scenario.get_game_context()
    
    # Create agents
    logger.info("Creating agents...")
    agents = {}
    for character_name, character_state in game_state.characters.items():
        logger.debug(f"  Creating agent: {character_name}")
        agent = GameAgent(
            character_name=character_name,
            character_state=character_state,
            llm_client=llm_client,
        )
        agents[character_name] = agent
    
    # Create gamemaster
    logger.info("Creating gamemaster...")
    gamemaster = GameMaster(
        llm_client=llm_client,
        random_seed=random_seed,
    )
    
    # Run simulation
    logger.info(f"Running simulation for {max_rounds} rounds...")
    results = run_simulation_sync(
        game_state=game_state,
        agents=agents,
        gamemaster=gamemaster,
        game_context=game_context,
        max_rounds=max_rounds,
    )
    
    # Print final state if verbose
    if verbose:
        print_character_states(
            game_state,
            title="Final Character States",
            log_level=logging.INFO
        )
    
    logger.info(f"Simulation complete: {results['rounds_completed']} rounds completed")
    
    return results

