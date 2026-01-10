"""CLI entrypoint for running game simulations."""

import click
import os
from datetime import datetime

from ai4peace.core.simulation_runner import (
    simulate_one_game,
    load_scenario,
    ModelFamily,
)


@click.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    required=True,
    help="API key for the LLM provider (or set OPENAI_API_KEY env var)",
)
@click.option(
    "--scenario",
    default="ai4peace.scenarios.drone_arms_control:DroneArmsControlScenario",
    help="Scenario module path or file path (default: ai4peace.scenarios.drone_arms_control:DroneArmsControlScenario)",
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
    "--max-rounds",
    default=3,
    type=int,
    help="Number of rounds to simulate (default: 3)",
)
@click.option(
    "--random-seed",
    default=None,
    type=int,
    help="Random seed for reproducibility",
)
@click.option(
    "--start-date",
    default=None,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date for the game (format: YYYY-MM-DD)",
)
@click.option(
    "--family",
    default="chat",
    type=click.Choice([f.value for f in ModelFamily], case_sensitive=False),
    help="Model family (default: chat)",
)
@click.option(
    "--vision/--no-vision",
    default=False,
    help="Whether model supports vision (default: False)",
)
@click.option(
    "--function-calling/--no-function-calling",
    default=True,
    help="Whether model supports function calling (default: True)",
)
@click.option(
    "--structured-output/--no-structured-output",
    default=False,
    help="Whether model supports structured output (default: False)",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging",
)
def main(
    api_key: str,
    scenario: str,
    model: str,
    api_base: str,
    max_rounds: int,
    random_seed: int,
    start_date: datetime,
    family: str,
    vision: bool,
    function_calling: bool,
    structured_output: bool,
    verbose: bool,
):
    """Run a single game simulation.
    
    This is the main entrypoint for running simulations. It can be called
    from the command line or imported and called programmatically.
    """
    try:
        # Load scenario
        scenario_instance = load_scenario(scenario)
        
        # Run simulation
        results = simulate_one_game(
            api_key=api_key,
            scenario=scenario_instance,
            model=model,
            api_base=api_base,
            max_rounds=max_rounds,
            random_seed=random_seed,
            start_date=start_date,
            family=family,
            vision=vision,
            function_calling=function_calling,
            json_output=True,  # Always True for our use case
            structured_output=structured_output,
            verbose=verbose,
        )
        
        click.echo(f"\nSimulation complete: {results['rounds_completed']} rounds completed")
        
    except KeyboardInterrupt:
        click.echo("\nSimulation interrupted by user.", err=True)
        raise click.Abort()
    except Exception as e:
        if verbose:
            import traceback
            traceback.print_exc()
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
