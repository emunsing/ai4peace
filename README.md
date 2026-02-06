# Strategic Multi-Agent Simulation Platform

A platform for using Autogen AgentChat to simulate interactions between different players/parties in an open-ended strategic role-playing game to study international technology policy development. This mirrors the behavior in strategic wargames used by think tanks (e.g., RAND, Institute for The Future) to simulate multi-party strategic decision making.

## Overview

The platform enables:
- **Multi-agent simulations** using LLM-powered agents instead of human players
- **Many simulation runs** to analyze game dynamics and study distributions of impacts
- **Round-based gameplay** where agents take actions and a gamemaster processes them
- **Information asymmetry** with private and public information per character
- **Complex actions** including research projects, espionage, lobbying, and negotiations

## Quick Start

Currently runs with: 

```
poetry run python -m new_architecture_runner --api-key sk-{your OpenAI key} --scenario ai4peace.core_v2.
research_strategy_scenario_basic_ai_race:BasicAIRaceScenario
```
Or on Novita:
```
poetry run python -m new_architecture_runner \
--api-key $NOVITA_API_KEY
--scenario ai4peace.core_v2.research_strategy_scenario_basic_ai_race:BasicAIRaceScenario
--api-base https://api.novita.ai/openai \
--model openai/gpt-oss-120b\ 
```

## Installation

```bash
# Install dependencies
poetry install

# Or with pip
pip install autogen-agentchat autogen-ext[openai]
```
## Research Applications

This platform enables:
- **Distributional analysis**: Run many simulations to study outcome distributions
- **Sensitivity analysis**: Test how different parameters affect outcomes
- **Policy impact studies**: Model effects of proposed regulations
- **Strategic planning**: Explore different strategic approaches

## Extending the Platform

### Creating a New Scenario Quickstart

1. Create a new file in `ai4peace/scenarios/`
2. Implement:
   - `create_game_state()`: Initialize game state
   - `create_characters()`: Define all characters
   - `get_game_context()`: Shared context description
3. Use the scenario in your simulation

### Customizing Agents

Agents are configured through:
- Character state (objectives, strategy, resources)
- System message template
- Available actions and tools

### Customizing Gamemaster

The gamemaster processes actions through:
- `_process_action()`: Handles each action type
- `_update_research_projects()`: Simulates research progress
- `_generate_summaries()`: Creates character-specific updates

### More detail: Create and run a new scenario

1. Copy one of the existing examples in `scenarios/` and give your new scenario a name.
2. Edit the system prompt in `get_game_context` with the Background, Current Situation, 
and Key Consideration (a major new development or focusing theme) for your simulation 
3. For each of your agentic roles, create a character by defining a function 
`create_character_name()`.
This includes the following fields for each character (feel free to prompt an LLM to help 
fill them in, or craft purely-human prose :)
* name
* true/private info (only known to the character): their "objectives" (str), "strategy" 
(str), "budget" (dict[str, float] for a given year and a budget in USD), and asset 
balance: "technical_capability" (float 0.0-100.0), "capital" (int for USD), and "human" (a 
float for the number of unallocated employees)
* stated/public info (visible to other characters): their "stated_objectives" (str), 
"stated_strategy" (str), and any "public_artifacts" (list[str] of products/services they 
offer)

For now, the game mechanics, victory conditions, possible actions, and public/private 
character information fields are fixed in prompts and code.
This is straightforward to extend/modify if you make changes in both code & prompts.
4. In the same file, optionally define a list of `RESEARCH_TOPICS` and `RANDOM_EVENTS` you 
know you'd like to include in the simulation as context. Note: right now the research 
topics are not used as an explicit filter.
5. Check the system prompt in `_build_system_message()` (in `core/agent.py`) to make sure 
it fits with your scenario (will be templated soon!)
6. Add imports for your new scenario in `scenarios/__init__.py`.
7. Run your scenario with
```
poetry run python simulate.py --api_key sk-{..} --scenario ai4peace.scenarios.
your_new_scenario_module:YourNewScenarioClass
```

## Example Scenario: Arms Control on Autonomous Drones

### Background

This scenario models the development and potential regulation of autonomous drone technologies in the context of:
- The ongoing Russia-Ukraine conflict
- Potential future Western-Russian conflicts
- Potential future US-China conflicts
- Evolving international norms around autonomous weapons systems

### Characters

**Western/Ukrainian Side:**
- Ukrainian Drone Startup: Battlefield-focused, needs funding
- Anduril Industries: Leading US defense tech company
- US Government (DoD): Large budget, strategic objectives

**Russian/Iranian Side:**
- Russian Government (Ministry of Defense): Large resources, asymmetric approach
- Iranian Drone Manufacturer: Cost-effective solutions, export-focused

### Research Topics

Agents can research various autonomous drone capabilities:
- Jamming improvements
- Long-distance mothership drones
- Autonomous tracking systems (short and long range)
- Scout drones with autonomous target selection
- Loitering drones with autonomous targeting
- Mothership deployment systems
- Automated defense systems (surface-to-air, anti-ICBM, anti-hypersonic)

### Available Actions

- **Fundraising**: Request budget increases or raise capital
- **Research Projects**: Create new research initiatives
- **Cancel Projects**: Free up resources
- **Capital Investment**: Invest in infrastructure
- **Sell Capital**: Divest assets
- **Espionage**: Gather intelligence on other characters
- **Poach Talent**: Recruit from other organizations
- **Lobbying**: Influence public opinion (may backfire)
- **Marketing**: Public campaigns
- **Private Messages**: Direct negotiations

## Architecture, Core Components & Game Flow

Coming soon!

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

