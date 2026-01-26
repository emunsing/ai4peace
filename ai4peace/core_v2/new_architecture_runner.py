import datetime
import click
import json
import logging
from typing import Optional
from ai4peace.core.simulation_runner import load_scenario_class, create_llm_client
from ai4peace.core_v2.new_architecture_draft import GameScenario
from ai4peace.core.utils import setup_logging

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

@click.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    required=True,
    help="OpenAI API key (or set OPENAI_API_KEY env var)",
)
@click.option(
    "--scenario",
    default="ai4peace.core_v2.cardgame_example:GoFishScenario",
    help="Scenario module path or file path (default: ai4peace.core_v2.cardgame_example:GoFishScenario)",
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
    "--log-file",
    default=f"v2_transcript_{datetime.datetime.now().replace(microsecond=0).isoformat()}.jsonl",
    type=str,
    help="Save the game transcript to this file",
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
        log_file: str,
        json_kwargs: str,
):
    """Run a single game simulation.

    This is the main entrypoint for running simulations. It can be called
    from the command line or imported and called programmatically.

    Example:
        python -m ai4peace.core.new_architecture_draft --api-key $OPENAI_API_KEY --json-kwargs '{"n_players": 3, "random_seed": 42}'
    """
    # Set up logging
    setup_logging(log_file=log_file) 

    # Load scenario
    scenario_class = load_scenario_class(scenario, must_subclass=GameScenario)

    llm_client = create_llm_client(
        api_key=api_key,
        model=model,
        api_base=api_base,
    )

    kwargs = json.loads(json_kwargs)
    scenario_instance = scenario_class(llm_client=llm_client, **kwargs)

    gamemaster = scenario_instance.get_game_master()
    gamemaster.run_simulation()

if __name__ == "__main__":
    main()