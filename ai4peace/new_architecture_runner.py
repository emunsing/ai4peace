import datetime
import click
import json
import logging
import asyncio
import multiprocessing
import os.path
from typing import Optional
from ai4peace.new_architecture_draft import GameScenario
from ai4peace.utils import setup_logging, load_scenario_class, create_llm_client

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
    default="ai4peace.cardgame_example:GoFishScenario",
    help="Scenario module path or file path (default: ai4peace.cardgame_example:GoFishScenario)",
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
@click.option(
    "--n-jobs",
    default=1,
    type=int,
    help="Number of parallel jobs to run (default: 1)",
)
def simulation_runner_cli(
        api_key: str,
        scenario: str,
        model: str,
        api_base: Optional[str],
        log_file: str,
        json_kwargs: str,
        n_jobs: int,
):
    """Run a single game simulation.

    This is the main entrypoint for running simulations. It can be called
    from the command line or imported and called programmatically.

    Example:
        python -m ai4peace.new_architecture_draft --api-key $OPENAI_API_KEY --json-kwargs '{"n_players": 3, "random_seed": 42}'
    """
    if n_jobs > 1:
        run_multiprocessing_simulations(
            api_key=api_key,
            scenario=scenario,
            model=model,
            api_base=api_base,
            log_file=log_file,
            json_kwargs=json_kwargs,
            n_jobs=n_jobs,
        )
    else:
        simulation_runner(
            api_key=api_key,
            scenario=scenario,
            model=model,
            api_base=api_base,
            log_file=log_file,
            json_kwargs=json_kwargs,
        )


def _generate_numbered_log_file(log_file: str, job_number: int) -> str:
    stem, ext = os.path.splitext(log_file)
    return f"{stem}_{job_number}{ext}"


def _run_single_simulation(args):
    # Needed because multiprocessing.Pool.map() requires that functions take a single argument (a tuple of arguments).
    (api_key, scenario, model, api_base, log_file, json_kwargs) = args
    simulation_runner(
        api_key=api_key,
        scenario=scenario,
        model=model,
        api_base=api_base,
        log_file=log_file,
        json_kwargs=json_kwargs,
    )

def run_multiprocessing_simulations(
        api_key: str,
        scenario: str,
        model: str,
        api_base: Optional[str],
        log_file: str,
        json_kwargs: str,
        n_jobs: int,
):
    logger.info(f"Starting {n_jobs} parallel simulation jobs")
    
    args_list = []
    for job_num in range(n_jobs):
        numbered_log_file = _generate_numbered_log_file(log_file, job_num)
        args_list.append((
            api_key,
            scenario,
            model,
            api_base,
            numbered_log_file,
            json_kwargs,
        ))
        logger.info(f"Job {job_num} will write to: {numbered_log_file}")
    
    # Run simulations in parallel
    with multiprocessing.Pool(processes=n_jobs) as pool:
        pool.map(_run_single_simulation, args_list)
    
    logger.info(f"Completed {n_jobs} parallel simulation jobs")

def simulation_runner(
        api_key: str,
        scenario: str,
        model: str,
        api_base: Optional[str],
        log_file: str,
        json_kwargs: str,
):
    """Run a single game simulation.
    
    Args:
        api_key: API key for LLM client
        scenario: Scenario module path
        model: Model name to use
        api_base: Custom API base URL for alternative providers (optional)
        log_file: Log file path
        json_kwargs: JSON string with scenario parameters
    """
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
    asyncio.run(gamemaster.run_simulation())


if __name__ == "__main__":
    simulation_runner_cli()