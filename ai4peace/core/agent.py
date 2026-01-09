"""Agent wrapper around Autogen for game participation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import asyncio
import re

from autogen_agentchat.agents import AssistantAgent

from .game_state import GameState, CharacterState
from .actions import Action, ActionType, ResearchProjectAction, MessageAction, EspionageAction
from .memory import MemoryStore


class GameAgent:
    """Wrapper around Autogen agent for game participation."""
    
    def __init__(
        self,
        character_name: str,
        character_state: CharacterState,
        llm_client: Any,
        memory_store: Optional[MemoryStore] = None,
        system_message_template: Optional[str] = None,
    ):
        """Initialize a game agent.
        
        Args:
            character_name: Name of the character
            character_state: Current state of the character
            llm_client: Autogen LLM client
            memory_store: Optional memory store for RAG
            system_message_template: Optional custom system message template
        """
        self.character_name = character_name
        self.character_state = character_state
        self.llm_client = llm_client
        self.memory_store = memory_store or MemoryStore()
        
        # Build system message
        self.system_message = self._build_system_message(system_message_template)
                
        pythonic_name = re.sub('\W|^(?=\d)','_', self.character_name)

        self.agent = AssistantAgent(
            name=pythonic_name,
            model_client=llm_client,
            system_message=self.system_message,
            tools=[],  # Can add tools here for RAG memory
        )
    
    def _build_system_message(self, template: Optional[str] = None) -> str:
        """Build the system message for the agent."""
        if template:
            return template
        
        private = self.character_state.private_info
        public = self.character_state.public_view
        
        system_message = f"""You are {self.character_name}, a participant in an international technology policy simulation focused on arms controls for autonomous drones.

## Your Identity and Goals

{private.objectives}

## Your Strategy

{private.strategy}

## Format for Your Responses

You must respond with a JSON object containing:
1. "actions": A list of actions you want to take this round
2. "messages": A list of private messages to send to other characters (optional)

### Action Format

Each action in "actions" should be one of:
- {{"type": "fundraise", "amount": <float>, "description": "<str>"}}
- {{"type": "create_research_project", "project": {{"name": "<str>", "description": "<str>", "target_completion_date": "<ISO date>", "annual_budget": <float>, "required_assets": {{"technical_capability": <float>, "capital": <float>, "human": <float>}}}}}}
- {{"type": "cancel_research_project", "project_name": "<str>"}}
- {{"type": "invest_capital", "amount": <float>}}
- {{"type": "sell_capital", "amount": <float>}}
- {{"type": "espionage", "target": "<character name>", "budget": <float>, "focus": "<what to investigate>"}}
  Or alternatively: {{"type": "espionage", "espionage": {{"target_character": "<name>", "budget": <float>, "focus": "<what>"}}}}
- {{"type": "poach_talent", "target": "<character name>", "budget": <float>}}
- {{"type": "lobby", "message": "<str>", "budget": <float>}}
- {{"type": "marketing", "message": "<str>", "budget": <float>}}

### Message Format

Each message in "messages" should be:
{{"to": "<character name>", "content": "<message text>"}}

Always respond with valid JSON only, no additional text."""
        
        return system_message
    
    def get_prompt_for_round(
        self,
        game_state: GameState,
        game_context: str,
        action_summary: str,
        private_updates: str,
    ) -> str:
        """Build the prompt for a specific round."""
        
        # Get recent actions
        recent_actions = "\n".join(self.character_state.recent_actions[-5:])
        
        # Get messages for this round
        current_messages = self.character_state.get_messages_for_round(game_state.round_number)
        message_text = ""
        if current_messages:
            message_text = "\n\n## Private Messages Received:\n"
            for msg in current_messages:
                message_text += f"\nFrom {msg.from_character}: {msg.content}\n"
        
        # Get available actions
        available_actions = self._get_available_actions_description(game_state)
        
        prompt = f"""## Game Context

{game_context}

## Current Game Date
{game_state.current_date.strftime('%Y-%m-%d')}

## Round {game_state.round_number}

### Global Game State Summary
{action_summary}

### Your Recent Actions
{recent_actions if recent_actions else "None yet"}
{message_text}

### Your Private Updates
{private_updates}

### Your Current Resources
- Budget: ${self.character_state.private_info.get_current_budget(game_state.current_date):,.0f}
- Assets:
  * Technical Capability: {self.character_state.private_info.true_asset_balance.technical_capability:.2f}
  * Capital: {self.character_state.private_info.true_asset_balance.capital:.2f}
  * Human Resources: {self.character_state.private_info.true_asset_balance.human:.2f}

### Active Research Projects
{self._format_projects()}

{available_actions}

What actions do you want to take this round? Respond with a JSON object as specified in your system message."""
        
        return prompt
    
    def _get_available_actions_description(self, game_state: GameState) -> str:
        """Get description of available actions."""
        return """
## Available Actions

You can take multiple actions per round. Consider:
1. **Fundraising** - Request budget increases or raise capital
2. **Research Projects** - Create new research initiatives (will consume budget and assets)
3. **Cancel Projects** - Free up resources by cancelling research
4. **Capital Investment** - Invest in infrastructure, factories, compute, etc.
5. **Sell Capital** - Divest assets to raise funds
6. **Espionage** - Gather intelligence on other characters
7. **Poach Talent** - Attempt to recruit from other organizations
8. **Lobbying** - Influence public opinion and policy (may backfire)
9. **Marketing** - Promote your position publicly
10. **Private Messages** - Negotiate with other characters directly
"""
    
    def _format_projects(self) -> str:
        """Format current research projects."""
        if not self.character_state.private_info.projects:
            return "None"
        
        lines = []
        for project in self.character_state.private_info.projects:
            if project.status == "active":
                lines.append(
                    f"- {project.name}: {project.progress*100:.0f}% complete, "
                    f"target: {project.target_completion_date.strftime('%Y-%m-%d')}"
                )
        return "\n".join(lines) if lines else "None"
    
    async def take_turn(
        self,
        game_state: GameState,
        game_context: str,
        action_summary: str,
        private_updates: str,
    ) -> Action:
        """Have the agent take its turn."""
        
        prompt = self.get_prompt_for_round(
            game_state, game_context, action_summary, private_updates
        )
        
        # Use Autogen to get response
        # For now, using a synchronous approach - can be made async
        response = await self._get_llm_response(prompt)
        
        # Parse response into actions
        actions = self._parse_response(response)
        
        return actions
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM via Autogen."""
        try:
            # Use autogen-ext's message types instead of plain dictionaries
            # Autogen-ext expects typed message objects, not dicts
            if SystemMessage is None or HumanMessage is None:
                raise ImportError("autogen-agentchat not installed. Install with: pip install autogen-agentchat")
            
            messages = [
                SystemMessage(content=self.system_message),
                HumanMessage(content=prompt)
            ]
            
            # Check if client has async create method
            if hasattr(self.llm_client, 'create'):
                create_method = self.llm_client.create
                if asyncio.iscoroutinefunction(create_method):
                    response = await create_method(messages=messages)
                else:
                    # Run sync method in executor
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        create_method,
                        messages
                    )
            else:
                # Try alternative method name
                if hasattr(self.llm_client, 'create_chat_completion'):
                    create_method = self.llm_client.create_chat_completion
                    if asyncio.iscoroutinefunction(create_method):
                        response = await create_method(messages=messages)
                    else:
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(
                            None,
                            create_method,
                            messages
                        )
                else:
                    raise AttributeError("LLM client has no create method")
            
            # Extract content from response
            # Handle various response formats
            if isinstance(response, str):
                return response
            elif hasattr(response, 'choices') and len(response.choices) > 0:
                # Standard OpenAI format - extract from choice
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content
                elif hasattr(choice, 'content'):
                    return choice.content
            elif hasattr(response, 'content'):
                # Direct content attribute
                return response.content
            elif hasattr(response, 'text'):
                # Some response formats use 'text'
                return response.text
            else:
                # Fallback: try to stringify
                return str(response)
                
        except Exception as e:
            # Fallback: return a basic structured response
            print(f"Warning: LLM call failed: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({
                "actions": [],
                "messages": []
            })
    
    def _parse_response(self, response_text: str) -> Action:
        """Parse agent response into Action objects."""
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            # Try to parse the whole thing
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse response as JSON: {response_text}")
        else:
            data = json.loads(json_match.group())
        
        # Parse actions
        actions_data = data.get("actions", [])
        messages_data = data.get("messages", [])
        
        # For now, we'll create a single Action object that can represent multiple actions
        # In a more complete implementation, you might want to return a list
        # For simplicity, we'll take the first action
        
        if not actions_data:
            # Default: no action
            return Action(
                action_type=ActionType.MESSAGE,  # Dummy type
                character_name=self.character_name,
                round_number=0,
            )
        
        first_action = actions_data[0]
        action_type_str = first_action.get("type", "")
        
        # Map to ActionType and create Action object
        action = self._create_action_from_dict(first_action, messages_data)
        
        return action
    
    def _create_action_from_dict(self, action_dict: Dict, messages: List[Dict]) -> Action:
        """Create an Action object from a dictionary."""
        action_type_map = {
            "fundraise": ActionType.FUNDRAISE,
            "create_research_project": ActionType.CREATE_RESEARCH_PROJECT,
            "cancel_research_project": ActionType.CANCEL_RESEARCH_PROJECT,
            "invest_capital": ActionType.INVEST_CAPITAL,
            "sell_capital": ActionType.SELL_CAPITAL,
            "espionage": ActionType.ESPIONAGE,
            "poach_talent": ActionType.POACH_TALENT,
            "lobby": ActionType.LOBBY,
            "marketing": ActionType.MARKETING,
        }
        
        action_type_str = action_dict.get("type", "")
        action_type = action_type_map.get(action_type_str, ActionType.MESSAGE)
        
        action = Action(
            action_type=action_type,
            character_name=self.character_name,
            round_number=0,  # Will be set by game master
        )
        
        # Fill in action-specific fields
        if action_type == ActionType.FUNDRAISE:
            action.fundraising_amount = action_dict.get("amount")
            action.fundraising_description = action_dict.get("description")
        elif action_type == ActionType.CREATE_RESEARCH_PROJECT:
            project_data = action_dict.get("project", {})
            action.research_project = ResearchProjectAction(
                name=project_data.get("name", ""),
                description=project_data.get("description", ""),
                target_completion_date=project_data.get("target_completion_date", ""),
                annual_budget=project_data.get("annual_budget", 0.0),
                required_assets=project_data.get("required_assets", {}),
            )
        elif action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            action.project_name_to_cancel = action_dict.get("project_name")
        elif action_type == ActionType.INVEST_CAPITAL:
            action.capital_investment = action_dict.get("amount")
        elif action_type == ActionType.SELL_CAPITAL:
            action.capital_to_sell = action_dict.get("amount")
        elif action_type == ActionType.ESPIONAGE:
            # Handle both flat format and nested format
            if "espionage" in action_dict and isinstance(action_dict["espionage"], dict):
                esp_data = action_dict["espionage"]
            else:
                esp_data = action_dict
            action.espionage = EspionageAction(
                target_character=esp_data.get("target") or esp_data.get("target_character", ""),
                budget=esp_data.get("budget", 0.0),
                focus=esp_data.get("focus", ""),
            )
        elif action_type == ActionType.POACH_TALENT:
            action.poaching_target = action_dict.get("target")
            action.poaching_budget = action_dict.get("budget")
        elif action_type == ActionType.LOBBY:
            action.lobbying_message = action_dict.get("message")
            action.lobbying_budget = action_dict.get("budget")
        elif action_type == ActionType.MARKETING:
            action.marketing_message = action_dict.get("message")
            action.marketing_budget = action_dict.get("budget")
        
        # Handle messages
        if messages:
            first_message = messages[0]
            action.message = MessageAction(
                to_character=first_message.get("to", ""),
                content=first_message.get("content", ""),
            )
        
        return action

