"""Utility functions for game state display and logging."""
import json
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Any
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ai4peace.new_architecture_draft import GameScenario

logger = logging.getLogger(__name__)
logging.getLogger("autogen_ext").setLevel(logging.ERROR)
logging.getLogger("autogen_core.events").setLevel(logging.WARNING)

class ModelFamily(str, Enum):
    """Valid model families for autogen-ext."""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"

def setup_logging(verbose: bool = False, log_file = "game_transcript.jsonl"):
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    transcript_logger = logging.getLogger('transcript')
    transcript_logger.setLevel(logging.INFO)

    exp_handler = logging.FileHandler(log_file)
    class JSONLFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps(record.msg)
    exp_handler.setFormatter(JSONLFormatter())
    transcript_logger.addHandler(exp_handler)
    transcript_logger.propagate = False

    # turn down logging volume of these packages
    logging.getLogger("autogen_core.events").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return transcript_logger

def get_transcript_logger():
    """Get the experiment logger (call after setup_logging)"""
    return logging.getLogger('transcript')


def load_scenario_class(scenario_path: str, must_subclass=GameScenario):
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
                issubclass(attr, GameScenario) and
                attr is not GameScenario):
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
                    issubclass(attr, GameScenario) and
                    attr is not GameScenario):
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
    timeout: float = 30.0,
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
        "timeout": timeout,
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
