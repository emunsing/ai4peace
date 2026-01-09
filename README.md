# AI4Peace: Strategic Multi-Agent Simulation Platform

A platform for using Autogen AgentChat to simulate interactions between different players/parties in an open-ended strategic role-playing game simulating international technology policy development. This mirrors the behavior in strategic wargames used by think tanks (e.g., RAND, Institute for The Future) to simulate multi-party strategic decision making.

## Overview

The platform enables:
- **Multi-agent simulations** using LLM-powered agents instead of human players
- **Many simulation runs** to analyze game dynamics and study distributions of impacts
- **Round-based gameplay** where agents take actions and a gamemaster processes them
- **Information asymmetry** with private and public information per character
- **Complex actions** including research projects, espionage, lobbying, and negotiations

## Architecture

### Core Components

1. **Game State** (`ai4peace/core/game_state.py`): Manages all game state including character information, assets, budgets, and research projects
2. **Agents** (`ai4peace/core/agent.py`): Autogen-based agents that make decisions using LLMs
3. **Gamemaster** (`ai4peace/core/gamemaster.py`): Processes actions deterministically and generates summaries
4. **Simulation** (`ai4peace/core/simulation.py`): Orchestrates the round-based game loop
5. **Scenarios** (`ai4peace/scenarios/`): Specific game implementations

### Game Flow

1. **Initialization**: Create game state, agents, and gamemaster
2. **Round Loop**:
   - Each agent receives context and takes actions
   - Gamemaster processes all actions deterministically
   - Game state is updated
   - Summaries are generated for next round
3. **Repeat** for specified number of rounds

## Installation

```bash
# Install dependencies
poetry install

# Or with pip
pip install autogen-agentchat autogen-ext[openai]
```

## Quick Start

### Run the Drone Arms Control Simulation

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Optionally set model and number of rounds
export OPENAI_MODEL="gpt-4o-mini"  # or gpt-4, gpt-4-turbo, etc.
export MAX_ROUNDS=3

# Run the example simulation
python example_drone_simulation.py
```

### Using as a Package

```python
from ai4peace.core.game_state import GameState
from ai4peace.core.agent import GameAgent
from ai4peace.core.gamemaster import GameMaster
from ai4peace.core.simulation import run_simulation_sync
from ai4peace.scenarios.drone_arms_control import (
    create_game_state,
    get_game_context,
)

# Initialize components
game_state = create_game_state()
game_context = get_game_context()

# Create agents (with your LLM client)
agents = {}
for name, char_state in game_state.characters.items():
    agents[name] = GameAgent(
        character_name=name,
        character_state=char_state,
        llm_client=your_llm_client,
    )

# Create gamemaster
gamemaster = GameMaster(llm_client=your_llm_client)

# Run simulation
results = run_simulation_sync(
    game_state=game_state,
    agents=agents,
    gamemaster=gamemaster,
    game_context=game_context,
    max_rounds=5,
)
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

## Extending the Platform

### Creating a New Scenario

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

## Research Applications

This platform enables:
- **Distributional analysis**: Run many simulations to study outcome distributions
- **Sensitivity analysis**: Test how different parameters affect outcomes
- **Policy impact studies**: Model effects of proposed regulations
- **Strategic planning**: Explore different strategic approaches

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

