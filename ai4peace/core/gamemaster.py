"""Gamemaster system for processing actions and updating game state."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
import json

from .utils import get_transcript_logger
from .game_state import (
    GameState,
    CharacterState,
    AssetBalance,
    ResearchProject,
    Message,
    PrivateInfo,
    PublicView,
)
from .actions import Action, ActionType


# TODO: these should more generally come from the right scenario
from ..scenarios.basic_ai_race import RANDOM_EVENTS

class GameMaster:
    """Gamemaster that processes actions and updates game state."""
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        random_seed: Optional[int] = None,
    ):
        """Initialize the gamemaster.
        
        Args:
            llm_client: Optional LLM client for generating summaries
            random_seed: Optional seed for deterministic randomness
        """
        self.llm_client = llm_client
        self.random = random.Random(random_seed)
        self.transcript_logger = get_transcript_logger
    
    def process_round(
        self,
        game_state: GameState,
        actions: List[Action],
    ) -> Dict[str, str]:
        """Process a round of actions and return summaries for each character.
        
        Args:
            game_state: Current game state
            actions: List of actions taken this round
            
        Returns:
            Dictionary mapping character names to their private update summaries
        """
        # Step 1: Increment time
        game_state.increment_round()
        
        # Step 2: Process bilateral messages
        self._process_messages(game_state, actions)
        
        # Step 3: Process character-specific actions
        for action in actions:
            self._process_action(game_state, action)
        
        # Step 4: Update research projects
        self._update_research_projects(game_state)
        
        # Step 5: Simulate espionage results
        self._simulate_espionage_results(game_state)
        
        # Step 6: Simulate information leaks
        self._simulate_information_leaks(game_state)
        
        # Step 7: Introduce random events
        self._introduce_random_events(game_state)
        
        # Step 8: Generate summaries
        summaries = self._generate_summaries(game_state, actions)
        
        return summaries
    
    def _process_messages(self, game_state: GameState, actions: List[Action]):
        """Process private messages between characters."""
        for action in actions:
            if action.message:
                to_char = game_state.get_character(action.message.to_character)
                if to_char:
                    message = Message(
                        from_character=action.character_name,
                        to_character=action.message.to_character,
                        content=action.message.content,
                        timestamp=game_state.current_date,
                        round_number=game_state.round_number,
                    )
                    to_char.add_message(message)
    
    def _process_action(self, game_state: GameState, action: Action):
        """Process a single action."""
        character = game_state.get_character(action.character_name)
        if not character:
            return
        
        action.round_number = game_state.round_number
        action_summary = ""
        
        if action.action_type == ActionType.FUNDRAISE:
            action_summary = self._process_fundraising(character, action)
        elif action.action_type == ActionType.CREATE_RESEARCH_PROJECT:
            action_summary = self._process_create_research(character, action, game_state)
        elif action.action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            action_summary = self._process_cancel_research(character, action)
        elif action.action_type == ActionType.INVEST_CAPITAL:
            action_summary = self._process_capital_investment(character, action)
        elif action.action_type == ActionType.SELL_CAPITAL:
            action_summary = self._process_sell_capital(character, action)
        elif action.action_type == ActionType.ESPIONAGE:
            action_summary = self._process_espionage(character, action, game_state)
        elif action.action_type == ActionType.POACH_TALENT:
            action_summary = self._process_poaching(character, action, game_state)
        elif action.action_type == ActionType.LOBBY:
            action_summary = self._process_lobbying(character, action)
        elif action.action_type == ActionType.MARKETING:
            action_summary = self._process_marketing(character, action)
        
        self.transcript_logger.info(action_summary)
        # Record action
        character.recent_actions.append(
            f"Round {game_state.round_number}: {action_summary}"
        )
        # Keep only last 5
        character.recent_actions = character.recent_actions[-5:]
    
    def _process_fundraising(self, character: CharacterState, action: Action) -> str:
        """Process fundraising action."""
        if action.fundraising_amount:
            # Determine success based on various factors
            success_prob = 0.7  # Base success rate
            success = self.random.random() < success_prob
            
            if success:
                # Add to budget
                year = str(datetime.now().year)
                current_budget = character.private_info.budget.get(year, 0.0)
                character.private_info.budget[year] = current_budget + action.fundraising_amount * 0.8  # 80% of requested
                return f"Successfully raised ${action.fundraising_amount * 0.8:,.0f}"
            else:
                return f"Fundraising attempt for ${action.fundraising_amount:,.0f} was unsuccessful"
        return "Fundraising action with no amount specified"
    
    def _process_create_research(
        self,
        character: CharacterState,
        action: Action,
        game_state: GameState,
    ) -> str:
        """Process research project creation."""
        if not action.research_project:
            return "Research project creation with no project details"
        
        project_data = action.research_project
        
        # Check if character has sufficient resources
        required = AssetBalance(
            technical_capability=project_data.required_assets.get("technical_capability", 0),
            capital=project_data.required_assets.get("capital", 0),
            human=project_data.required_assets.get("human", 0),
        )
        
        current = character.private_info.true_asset_balance
        
        if (current.technical_capability < required.technical_capability or
            current.capital < required.capital or
            current.human < required.human):
            return f"Insufficient resources to start research project '{project_data.name}'"
        
        # Check budget
        year = str(game_state.current_date.year)
        current_budget = character.private_info.budget.get(year, 0.0)
        if current_budget < project_data.annual_budget:
            return f"Insufficient budget for research project '{project_data.name}'"
        
        # Create project
        try:
            target_date = datetime.fromisoformat(project_data.target_completion_date)
        except ValueError:
            target_date = game_state.current_date + timedelta(days=365)
        
        project = ResearchProject(
            name=project_data.name,
            description=project_data.description,
            target_completion_date=target_date,
            committed_budget=project_data.annual_budget,
            committed_assets=required,
            status="active",
            progress=0.0,
        )
        
        # Deduct resources
        character.private_info.true_asset_balance = current.subtract(required)
        character.private_info.budget[year] = current_budget - project_data.annual_budget
        
        # Assess realism
        project.realistic_goals = self._assess_research_realism(project, character)
        character.private_info.projects.append(project)
        
        return f"Created research project '{project_data.name}'"
    
    def _process_cancel_research(self, character: CharacterState, action: Action) -> str:
        """Process research project cancellation."""
        if not action.project_name_to_cancel:
            return "Cancel action with no project name"
        
        # Find and cancel project
        for project in character.private_info.projects:
            if project.name == action.project_name_to_cancel and project.status == "active":
                project.status = "cancelled"
                # Refund some resources (not all)
                refund = AssetBalance(
                    technical_capability=project.committed_assets.technical_capability * 0.5,
                    capital=project.committed_assets.capital * 0.5,
                    human=project.committed_assets.human * 0.5,
                )
                character.private_info.true_asset_balance = (
                    character.private_info.true_asset_balance.add(refund)
                )
                return f"Cancelled research project '{action.project_name_to_cancel}'"
        
        return f"Could not find active research project '{action.project_name_to_cancel}'"
    
    def _process_capital_investment(self, character: CharacterState, action: Action) -> str:
        """Process capital investment."""
        if not action.capital_investment:
            return "Capital investment with no amount"
        
        # Check if character has budget
        year = str(datetime.now().year)
        budget = character.private_info.budget.get(year, 0.0)
        if budget < action.capital_investment:
            return f"Insufficient budget for capital investment of ${action.capital_investment:,.0f}"
        
        # Invest: convert budget to capital assets
        character.private_info.budget[year] = budget - action.capital_investment
        character.private_info.true_asset_balance.capital += action.capital_investment * 0.9  # 90% conversion
        
        return f"Invested ${action.capital_investment:,.0f} in capital improvements"
    
    def _process_sell_capital(self, character: CharacterState, action: Action) -> str:
        """Process selling capital."""
        if not action.capital_to_sell:
            return "Sell capital with no amount"
        
        # Check if character has capital
        if character.private_info.true_asset_balance.capital < action.capital_to_sell:
            return f"Insufficient capital to sell ${action.capital_to_sell:,.0f}"
        
        # Sell: convert capital to budget
        character.private_info.true_asset_balance.capital -= action.capital_to_sell
        year = str(datetime.now().year)
        current_budget = character.private_info.budget.get(year, 0.0)
        character.private_info.budget[year] = current_budget + action.capital_to_sell * 0.7  # 70% conversion
        
        return f"Sold ${action.capital_to_sell:,.0f} in capital assets"
    
    def _process_espionage(
        self,
        character: CharacterState,
        action: Action,
        game_state: GameState,
    ) -> str:
        """Process espionage action."""
        if not action.espionage:
            return "Espionage action with no details"
        
        target = game_state.get_character(action.espionage.target_character)
        if not target:
            return f"Target character '{action.espionage.target_character}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = character.private_info.budget.get(year, 0.0)
        if budget < action.espionage.budget:
            return f"Insufficient budget for espionage"
        
        # Deduct budget
        character.private_info.budget[year] = budget - action.espionage.budget
        
        # Store espionage attempt (results processed later)
        # For now, we'll create a simple success indicator
        success_prob = min(0.3 + (action.espionage.budget / 1000000), 0.8)  # Scale with budget
        success = self.random.random() < success_prob
        
        # Store in character metadata (simplified - could use a more structured approach)
        if not hasattr(character, '_espionage_results'):
            character._espionage_results = []
        
        character._espionage_results.append({
            "target": action.espionage.target_character,
            "focus": action.espionage.focus,
            "budget": action.espionage.budget,
            "success": success,
            "round": game_state.round_number,
        })
        
        return f"Conducted espionage on {action.espionage.target_character} ({'success' if success else 'failed'})"
    
    def _process_poaching(
        self,
        character: CharacterState,
        action: Action,
        game_state: GameState,
    ) -> str:
        """Process talent poaching."""
        if not action.poaching_target or not action.poaching_budget:
            return "Poaching action with no target or budget"
        
        target = game_state.get_character(action.poaching_target)
        if not target:
            return f"Target character '{action.poaching_target}' not found"
        
        # Check budget
        year = str(game_state.current_date.year)
        budget = character.private_info.budget.get(year, 0.0)
        if budget < action.poaching_budget:
            return "Insufficient budget for poaching"
        
        # Deduct budget
        character.private_info.budget[year] = budget - action.poaching_budget
        
        # Determine success
        success_prob = min(0.2 + (action.poaching_budget / 500000), 0.6)
        success = self.random.random() < success_prob
        
        if success:
            # Transfer some human resources
            transfer_amount = min(target.private_info.true_asset_balance.human * 0.1, 5.0)
            target.private_info.true_asset_balance.human -= transfer_amount
            character.private_info.true_asset_balance.human += transfer_amount
            return f"Successfully poached talent from {action.poaching_target} (gained {transfer_amount:.1f} human resources)"
        else:
            return f"Poaching attempt on {action.poaching_target} failed"
    
    def _process_lobbying(self, character: CharacterState, action: Action) -> str:
        """Process lobbying action."""
        if not action.lobbying_message or not action.lobbying_budget:
            return "Lobbying action with no message or budget"
        
        # Check budget and deduct
        year = str(datetime.now().year)
        budget = character.private_info.budget.get(year, 0.0)
        if budget < action.lobbying_budget:
            return "Insufficient budget for lobbying"
        
        character.private_info.budget[year] = budget - action.lobbying_budget
        
        # Lobbying may backfire
        backfire_prob = 0.1
        if self.random.random() < backfire_prob:
            return f"Lobbying campaign backfired: {action.lobbying_message[:50]}..."
        else:
            return f"Launched lobbying campaign: {action.lobbying_message[:50]}..."
    
    def _process_marketing(self, character: CharacterState, action: Action) -> str:
        """Process marketing action."""
        if not action.marketing_message or not action.marketing_budget:
            return "Marketing action with no message or budget"
        
        # Check budget and deduct
        year = str(datetime.now().year)
        budget = character.private_info.budget.get(year, 0.0)
        if budget < action.marketing_budget:
            return "Insufficient budget for marketing"
        
        character.private_info.budget[year] = budget - action.marketing_budget
        return f"Launched marketing campaign: {action.marketing_message[:50]}..."
    
    def _update_research_projects(self, game_state: GameState):
        """Update all active research projects."""
        for character in game_state.characters.values():
            for project in character.private_info.projects:
                if project.status == "active":
                    # Simulate research progress
                    # Progress rate depends on committed resources
                    progress_rate = min(
                        0.1 + (project.committed_assets.human / 100),
                        0.3  # Max 30% per round
                    )
                    project.progress = min(project.progress + progress_rate, 1.0)
                    
                    # Check if completed
                    if project.progress >= 1.0:
                        project.status = "completed"
                    
                    # Deduct budget
                    year = str(game_state.current_date.year)
                    budget = character.private_info.budget.get(year, 0.0)
                    if budget >= project.committed_budget:
                        character.private_info.budget[year] = budget - project.committed_budget
    
    def _simulate_espionage_results(self, game_state: GameState):
        """Process espionage results and add to character private updates."""
        for character in game_state.characters.values():
            if hasattr(character, '_espionage_results'):
                for esp_result in character._espionage_results:
                    if esp_result.get("success"):
                        target = game_state.get_character(esp_result["target"])
                        if target:
                            # Add information to character's private updates
                            if not hasattr(character, '_private_updates'):
                                character._private_updates = []
                            character._private_updates.append(
                                f"Espionage on {esp_result['target']} ({esp_result['focus']}): "
                                f"Discovered budget ≈${target.private_info.budget.get(str(game_state.current_date.year), 0):,.0f}, "
                                f"assets: tech={target.private_info.true_asset_balance.technical_capability:.1f}, "
                                f"capital={target.private_info.true_asset_balance.capital:.1f}, "
                                f"human={target.private_info.true_asset_balance.human:.1f}"
                            )
                # Clear processed results
                character._espionage_results = []
    
    def _simulate_information_leaks(self, game_state: GameState):
        """Simulate information leaks through reporter investigations."""
        leak_prob = 0.05  # 5% chance per round of a leak
        if self.random.random() < leak_prob:
            # Select a random character
            character = self.random.choice(list(game_state.characters.values()))
            
            # Leak some information
            leak_info = (
                f"Leaked intelligence reports suggest {character.name} has "
                f"approximately ${character.private_info.budget.get(str(game_state.current_date.year), 0):,.0f} "
                f"in budget and {character.private_info.true_asset_balance.human:.1f} human resources."
            )
            
            # Update public view (partial information)
            # In a more sophisticated implementation, this would update public_view.asset_balance
            game_state.public_events.append(leak_info)
    
    def _introduce_random_events(self, game_state: GameState):
        """Introduce random external events."""
        event_prob = 0.1  # 10% chance per round
        if self.random.random() < event_prob:
            #events = [
            #    "Political shifts in international relations affect drone policy discussions.",
            #    "New technological breakthrough announced in autonomous systems.",
            ##    "Major conflict escalation impacts defense spending priorities.",
            ##    "Regulatory body proposes new guidelines for autonomous weapons.",
            ##
            #    "Public opinion shifts on autonomous military technology.",
            #]
            events = RANDOM_EVENTS
            event = self.random.choice(events)
            game_state.public_events.append(f"Round {game_state.round_number}: {event}")
    
    def _assess_research_realism(
        self,
        project: ResearchProject,
        character: CharacterState,
    ) -> Optional[str]:
        """Assess if research goals are realistic and modify if needed."""
        # Simple heuristic: check if timeline is reasonable given resources
        days_to_complete = (project.target_completion_date - datetime.now()).days
        required_resources = (
            project.committed_assets.human +
            project.committed_assets.technical_capability * 0.5 +
            project.committed_assets.capital * 0.3
        )
        
        # Rough estimate: need at least 10 resource-days per day of timeline
        if required_resources * days_to_complete < days_to_complete * 10:
            # Extend timeline
            project.target_completion_date = datetime.now() + timedelta(days=365)
            return "Timeline extended to be more realistic given available resources."
        
        return None
    
    def _generate_summaries(
        self,
        game_state: GameState,
        actions: List[Action],
    ) -> Dict[str, str]:
        """Generate summaries for each character."""
        summaries = {}
        
        # Create global action summary
        action_summary = self._create_action_summary(game_state, actions)
        
        # Generate character-specific summaries
        for character_name, character in game_state.characters.items():
            private_updates = []
            
            # Add espionage results
            if hasattr(character, '_private_updates'):
                private_updates.extend(character._private_updates)
                character._private_updates = []
            
            # Add research project updates
            for project in character.private_info.projects:
                if project.status == "completed":
                    private_updates.append(f"Research project '{project.name}' has been completed!")
                elif project.status == "active":
                    private_updates.append(
                        f"Research project '{project.name}' is {project.progress*100:.0f}% complete."
                    )
            
            summaries[character_name] = "\n".join(private_updates) if private_updates else "No significant private updates."
        
        # Store global summary
        game_state.game_history.append(action_summary)
        
        return summaries
    
    def _create_action_summary(
        self,
        game_state: GameState,
        actions: List[Action],
    ) -> str:
        """Create a summary of all actions taken this round."""
        summary_parts = [f"Round {game_state.round_number} Summary ({game_state.current_date.strftime('%Y-%m-%d')}):"]
        
        # Group actions by character
        by_character = {}
        for action in actions:
            if action.character_name not in by_character:
                by_character[action.character_name] = []
            by_character[action.character_name].append(action)
        
        for char_name, char_actions in by_character.items():
            summary_parts.append(f"\n{char_name}:")
            for action in char_actions:
                action_desc = self._describe_action(action)
                summary_parts.append(f"  - {action_desc}")
        
        # Add public events
        if game_state.public_events:
            summary_parts.append("\nPublic Events:")
            for event in game_state.public_events[-5:]:  # Last 5 events
                summary_parts.append(f"  - {event}")
        
        return "\n".join(summary_parts)
    
    def _describe_action(self, action: Action) -> str:
        """Create a human-readable description of an action."""
        if action.action_type == ActionType.FUNDRAISE:
            return f"Attempted fundraising of ${action.fundraising_amount or 0:,.0f}"
        elif action.action_type == ActionType.CREATE_RESEARCH_PROJECT:
            return f"Created research project: {action.research_project.name if action.research_project else 'unknown'}"
        elif action.action_type == ActionType.CANCEL_RESEARCH_PROJECT:
            return f"Cancelled research project: {action.project_name_to_cancel}"
        elif action.action_type == ActionType.INVEST_CAPITAL:
            return f"Invested ${action.capital_investment or 0:,.0f} in capital"
        elif action.action_type == ActionType.SELL_CAPITAL:
            return f"Sold ${action.capital_to_sell or 0:,.0f} in capital"
        elif action.action_type == ActionType.ESPIONAGE:
            return f"Conducted espionage on {action.espionage.target_character if action.espionage else 'unknown'}"
        elif action.action_type == ActionType.POACH_TALENT:
            return f"Attempted to poach talent from {action.poaching_target}"
        elif action.action_type == ActionType.LOBBY:
            return "Launched lobbying campaign"
        elif action.action_type == ActionType.MARKETING:
            return "Launched marketing campaign"
        elif action.action_type == ActionType.MESSAGE:
            return f"Sent message to {action.message.to_character if action.message else 'unknown'}"
        return "Unknown action"

