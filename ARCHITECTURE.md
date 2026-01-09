# Architecture Documentation

## Overview

The AI4Peace platform is a multi-agent simulation system for modeling strategic interactions in international technology policy. It uses Autogen AgentChat to create LLM-powered agents that participate in round-based games.

## Core Architecture

### Component Hierarchy

```
ai4peace/
├── core/                    # Core framework
│   ├── game_state.py       # Game state management
│   ├── actions.py          # Action system
│   ├── agent.py            # Agent wrapper around Autogen
│   ├── gamemaster.py       # Action processing and state updates
│   ├── simulation.py       # Main simulation orchestrator
│   └── memory.py           # RAG memory store
├── scenarios/               # Scenario implementations
│   └── drone_arms_control.py
└── example_drone_simulation.py  # Example usage
```

## Key Components

### GameState (`core/game_state.py`)

Manages all game state including:
- Current date and round number
- Character states (private and public information)
- Public events
- Game history

**Key Classes:**
- `GameState`: Main game state container
- `CharacterState`: State for a single character
- `PrivateInfo`: Private information (true assets, objectives, budget, projects)
- `PublicView`: Publicly visible information
- `AssetBalance`: Technical capability, capital, and human resources
- `ResearchProject`: Active research/investment projects
- `Message`: Private messages between characters

### Actions (`core/actions.py`)

Defines the action system:
- `Action`: Main action class
- `ActionType`: Enum of action types
- `ResearchProjectAction`: Details for creating research projects
- `EspionageAction`: Details for espionage
- `MessageAction`: Private messages

**Action Types:**
- Fundraising
- Create/Cancel research projects
- Capital investment/divestment
- Espionage
- Talent poaching
- Lobbying
- Marketing
- Private messages

### GameAgent (`core/agent.py`)

Wrapper around Autogen's `AssistantAgent` that:
- Manages character-specific prompts
- Integrates game context and state
- Parses LLM responses into actions
- Supports RAG memory (via `MemoryStore`)

**Key Methods:**
- `take_turn()`: Agent makes decisions for a round
- `get_prompt_for_round()`: Builds context-aware prompts
- `_parse_response()`: Converts LLM output to actions

### GameMaster (`core/gamemaster.py`)

Processes actions and updates game state:
- `process_round()`: Main processing entry point
- `_process_action()`: Handles each action type
- `_update_research_projects()`: Simulates research progress
- `_simulate_espionage_results()`: Processes espionage outcomes
- `_generate_summaries()`: Creates character-specific updates

**Processing Steps (per round):**
1. Increment time
2. Process messages
3. Process actions
4. Update research projects
5. Simulate espionage results
6. Simulate information leaks
7. Introduce random events
8. Generate summaries

### Simulation (`core/simulation.py`)

Orchestrates the game loop:
- Manages round-by-round execution
- Coordinates agents and gamemaster
- Maintains simulation history
- Provides synchronous and asynchronous interfaces

## Game Flow

1. **Initialization**
   - Create game state with characters
   - Initialize agents with LLM clients
   - Create gamemaster

2. **Round Loop**
   - Each agent receives:
     * Game context
     * Current game state summary
     * Their recent actions
     * Private updates
     * Available actions
   - Agents generate actions via LLM
   - Gamemaster processes all actions
   - Game state is updated
   - Summaries are generated for next round

3. **Termination**
   - After specified number of rounds
   - Results and history are returned

## Information Asymmetry

The system maintains information asymmetry:
- **Private Information**: True assets, actual objectives, budget details
- **Public Information**: Estimated/leaked information visible to all
- **Private Updates**: Espionage results, research progress, messages

## Research Projects

Research projects:
- Require budget and asset commitments
- Progress over time based on resources
- Can be cancelled (partial refund)
- Have realistic timelines assessed by gamemaster
- May complete and provide benefits (future: add benefits system)

## Extensibility

### Adding New Action Types

1. Add to `ActionType` enum in `actions.py`
2. Add handling in `GameMaster._process_action()`
3. Add parsing in `GameAgent._create_action_from_dict()`
4. Update system message template

### Creating New Scenarios

1. Create file in `scenarios/`
2. Implement:
   - `create_game_state()`: Initialize state
   - `create_characters()`: Define characters
   - `get_game_context()`: Shared context
3. Use in simulation

### Customizing Agents

- Modify system message templates
- Add tools/functions for RAG memory
- Customize prompt generation
- Adjust parsing logic

## Current Limitations

1. **Single Action per Turn**: Currently agents submit one action per round (plus messages). Can be extended to support multiple actions.

2. **Deterministic Processing**: Gamemaster uses deterministic logic with some randomness. More sophisticated simulation could use LLM for outcomes.

3. **Research Benefits**: Completed research projects don't yet grant benefits (beyond progress tracking). Can be extended.

4. **Public View Updates**: Public views aren't automatically updated based on leaks/events. Can be enhanced.

5. **RAG Memory**: Basic implementation. Can be enhanced with vector embeddings and semantic search.

## Future Enhancements

- Multi-action support per turn
- LLM-based gamemaster decision making
- Research project completion benefits
- Dynamic public view updates
- Advanced RAG with semantic search
- Visualization and analysis tools
- Export/import game states
- Replay and branching scenarios

