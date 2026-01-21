"""Wargame player implementation using LLM agents."""

import json
import re
import logging
from typing import Optional, Any, Dict, List
import datetime

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import BaseTextChatMessage

from .new_architecture_draft import Player
from .wargame_state import WargamePlayerState
from .wargame_actions import (
    WargamePlayerProposedMove,
    WargameMoveCorrectionMessage,
    ActionType,
    ResearchProjectAction,
    EspionageAction,
    MessageAction,
)
from .wargame_updates import WargameGamemasterUpdateMessage

logger = logging.getLogger(__name__)
logging.getLogger("autogen_core.events").setLevel(logging.WARNING)


class WargamePlayer(Player):
    """Player for wargame simulation using LLM agents."""
    
    def __init__(
        self,
        name: str,
        attributes: WargamePlayerState,
        llm_client: Any,
        system_message_template: Optional[str] = None,
        game_context: Optional[str] = None,
    ):
        """Initialize a wargame player.
        
        Args:
            name: Name of the character
            attributes: Current state of the character
            llm_client: Autogen LLM client
            system_message_template: Optional custom system message template
            game_context: Optional game context for building prompts
        """
        self.name = name
        self.attributes = attributes
        self.llm_client = llm_client
        self.game_context = game_context or ""
        
        # Build system message
        self.system_message = self._build_system_message(system_message_template)
        
        # Clean name for autogen (no special chars)
        self.clean_name = re.sub(r"\W|^(?=\d)", "_", self.name)
        
        logging.getLogger("autogen_agentchat").setLevel(logging.ERROR)
        self.agent = AssistantAgent(
            name=self.clean_name,
            model_client=llm_client,
            system_message=self.system_message,
            tools=[],  # Can add tools here for RAG memory
        )
        
        # Action history for tracking
        self.action_history: Dict = {}
    
    def _build_system_message(self, template: Optional[str] = None) -> str:
        """Build the system message for the agent."""
        if template:
            return template
        
        private = self.attributes.private_info
        public = self.attributes.public_view
        
        system_message = f"""You are {self.name}, a participant in an international technology policy simulation.

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
- {{"type": "poach_talent", "target": "<character name>", "budget": <float>}}
- {{"type": "lobby", "message": "<str>", "budget": <float>}}
- {{"type": "marketing", "message": "<str>", "budget": <float>}}

### Message Format

Each message in "messages" should be:
{{"to": "<character name>", "content": "<message text>"}}

Always respond with valid JSON only, no additional text."""
        
        return system_message
    
    def update_state(self, msg: WargameGamemasterUpdateMessage) -> None:
        """Update player state based on gamemaster message."""
        updates = msg.state_updates
        
        # Update budget
        for year, delta in updates.budget_changes.items():
            current = self.attributes.private_info.budget.get(year, 0.0)
            self.attributes.private_info.budget[year] = current + delta
        
        # Update asset balance
        if updates.asset_balance_changes:
            self.attributes.private_info.true_asset_balance = (
                self.attributes.private_info.true_asset_balance.add(updates.asset_balance_changes)
            )
        
        # Update research projects
        for project in updates.new_projects:
            self.attributes.private_info.projects.append(project)
        
        for project in updates.updated_projects:
            # Find and update existing project
            for i, p in enumerate(self.attributes.private_info.projects):
                if p.name == project.name:
                    self.attributes.private_info.projects[i] = project
                    break
        
        for project_name in updates.completed_projects:
            for project in self.attributes.private_info.projects:
                if project.name == project_name:
                    project.status = "completed"
                    break
        
        for project_name in updates.cancelled_projects:
            for project in self.attributes.private_info.projects:
                if project.name == project_name:
                    project.status = "cancelled"
                    break
        
        # Add messages
        for message in updates.new_messages:
            self.attributes.add_message(message)
        
        # Update public views of other players
        self.attributes.public_view = updates.other_players_public_views.get(
            self.name, self.attributes.public_view
        )
        
        # Store action results
        if updates.action_results:
            for result in updates.action_results:
                self.attributes.recent_actions.append(result)
            # Keep only last 5
            self.attributes.recent_actions = self.attributes.recent_actions[-5:]
        
        # Store in action history
        self.action_history[str(msg.last_action_timestamp)] = {
            "budget_changes": updates.budget_changes,
            "asset_balance_changes": updates.asset_balance_changes.to_dict() if updates.asset_balance_changes else None,
            "action_results": updates.action_results,
            "public_events": updates.public_events,
            "espionage_results": updates.espionage_results,
        }
    
    def propose_actions(self) -> WargamePlayerProposedMove:
        """Propose actions using LLM."""
        # This will be called by the gamemaster with appropriate context
        # For now, return empty move - the gamemaster will provide context
        return WargamePlayerProposedMove()
    
    async def propose_actions_with_context(
        self,
        game_state_summary: str,
        private_updates: str,
        current_date: datetime.datetime,
        round_number: int,
    ) -> WargamePlayerProposedMove:
        """Propose actions with full game context."""
        prompt = self._build_prompt(
            game_state_summary, private_updates, current_date, round_number
        )
        
        # Use Autogen to get response
        response = await self._get_llm_response(prompt)
        
        # Parse response into actions
        move = self._parse_response(response)
        
        return move
    
    def _build_prompt(
        self,
        game_state_summary: str,
        private_updates: str,
        current_date: datetime.datetime,
        round_number: int,
    ) -> str:
        """Build the prompt for a specific round."""
        # Get recent actions
        recent_actions = "\n".join(self.attributes.recent_actions[-5:])
        
        # Get messages for this round
        current_messages = self.attributes.get_messages_for_round(round_number)
        message_text = ""
        if current_messages:
            message_text = "\n\n## Private Messages Received:\n"
            for msg in current_messages:
                message_text += f"\nFrom {msg.from_character}: {msg.content}\n"
        
        prompt = f"""## Game Context

{self.game_context}

## Current Game Date
{current_date.strftime('%Y-%m-%d')}

## Round {round_number}

### Global Game State Summary
{game_state_summary}

### Your Recent Actions
{recent_actions if recent_actions else "None yet"}
{message_text}

### Your Private Updates
{private_updates}

### Your Current Resources
- Budget: ${self.attributes.private_info.get_current_budget(current_date):,.0f}
- Assets:
  * Technical Capability: {self.attributes.private_info.true_asset_balance.technical_capability:.2f}
  * Capital: {self.attributes.private_info.true_asset_balance.capital:.2f}
  * Human Resources: {self.attributes.private_info.true_asset_balance.human:.2f}

### Active Research Projects
{self._format_projects()}

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

What actions do you want to take this round? Respond with a JSON object as specified in your system message."""
        
        return prompt
    
    def _format_projects(self) -> str:
        """Format current research projects."""
        if not self.attributes.private_info.projects:
            return "None"
        
        lines = []
        for project in self.attributes.private_info.projects:
            if project.status == "active":
                lines.append(
                    f"- {project.name}: {project.progress*100:.0f}% complete, "
                    f"target: {project.target_completion_date.strftime('%Y-%m-%d')}"
                )
        return "\n".join(lines) if lines else "None"
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM via Autogen."""
        try:
            messages = [
                BaseTextChatMessage(source=self.clean_name, content=self.system_message),
                BaseTextChatMessage(source=self.clean_name, content=prompt)
            ]
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name} - System message length: {len(self.system_message)} chars")
                logger.debug(f"{self.name} - Prompt length: {len(prompt)} chars")
            
            response = await self.agent.run(task=messages)
            response_content = response.messages[-1].content if response.messages else ""
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self.name} - Response length: {len(response_content)} chars")
                logger.debug(f"{self.name} - Full response:\n{response_content}")
            
            return response_content
                
        except Exception as e:
            logger.error(f"{self.name} - LLM call failed: {e}", exc_info=True)
            return json.dumps({
                "actions": [],
                "messages": []
            })
    
    def _parse_response(self, response_text: str) -> WargamePlayerProposedMove:
        """Parse agent response into WargamePlayerProposedMove."""
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(f"{self.name} - Could not parse response as JSON: {response_text}")
                return WargamePlayerProposedMove()
        else:
            data = json.loads(json_match.group())
        
        # Parse actions
        actions_data = data.get("actions", [])
        messages_data = data.get("messages", [])
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self.name} - Parsed {len(actions_data)} actions, {len(messages_data)} messages")
        
        # Create moves from actions
        moves = []
        for action_dict in actions_data:
            move = self._create_move_from_dict(action_dict, messages_data)
            if move.action_type:  # Only add if valid
                moves.append(move)
        
        # Return first move (or empty if none)
        if moves:
            primary_move = moves[0]
            if len(moves) > 1:
                primary_move.additional_actions = moves[1:]
            return primary_move
        
        return WargamePlayerProposedMove()
    
    def _create_move_from_dict(
        self, action_dict: Dict, messages: List[Dict]
    ) -> WargamePlayerProposedMove:
        """Create a WargamePlayerProposedMove from a dictionary."""
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
        action_type = action_type_map.get(action_type_str)
        
        move = WargamePlayerProposedMove(action_type=action_type)
        
        # Fill in action-specific fields
        if action_type == ActionType.FUNDRAISE:
            move.fundraising_amount = action_dict.get("amount")
            move.fundraising_description = action_dict.get("description")
        elif action_type == ActionType.CREATE_RESEARCH_PROJECT:
            project_data = action_dict.get("project", {})
            move.research_project = ResearchProjectAction(
                name=project_data.get("name", ""),
                description=project_data.get("description", ""),
                target_completion_date=project_data.get("target_completion_date", ""),
                annual_budget=project_data.get("annual_budget", 0.0),
                required_assets=project_data.get("required_assets", {}),
            )
        elif action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            move.project_name_to_cancel = action_dict.get("project_name")
        elif action_type == ActionType.INVEST_CAPITAL:
            move.capital_investment = action_dict.get("amount")
        elif action_type == ActionType.SELL_CAPITAL:
            move.capital_to_sell = action_dict.get("amount")
        elif action_type == ActionType.ESPIONAGE:
            esp_data = action_dict
            move.espionage = EspionageAction(
                target_character=esp_data.get("target") or esp_data.get("target_character", ""),
                budget=esp_data.get("budget", 0.0),
                focus=esp_data.get("focus", ""),
            )
        elif action_type == ActionType.POACH_TALENT:
            move.poaching_target = action_dict.get("target")
            move.poaching_budget = action_dict.get("budget")
        elif action_type == ActionType.LOBBY:
            move.lobbying_message = action_dict.get("message")
            move.lobbying_budget = action_dict.get("budget")
        elif action_type == ActionType.MARKETING:
            move.marketing_message = action_dict.get("message")
            move.marketing_budget = action_dict.get("budget")
        
        # Handle messages (attach first message to this move)
        if messages:
            first_message = messages[0]
            move.message = MessageAction(
                to_character=first_message.get("to", ""),
                content=first_message.get("content", ""),
            )
        
        return move
    
    def correct_moves(
        self, move_modifications: WargameMoveCorrectionMessage
    ) -> WargamePlayerProposedMove:
        """Correct moves based on gamemaster feedback."""
        logger.info(f"{self.name} - Move corrected: {move_modifications.error_message}")
        
        if move_modifications.suggested_correction:
            return move_modifications.suggested_correction
        
        # If no suggested correction, return empty move
        return WargamePlayerProposedMove()

