"""Utility functions for game state display and logging."""

import logging
from typing import Optional

from .game_state import GameState


logger = logging.getLogger(__name__)


def print_character_states(
    game_state: GameState,
    title: str = "Character States",
    log_level: int = logging.INFO,
):
    """Print the current state of all characters.
    
    Args:
        game_state: Current game state
        title: Optional title for the section
        log_level: Logging level to use (default: INFO)
    """
    message = f"\n{'-'*60}\n{title}\n{'-'*60}\n"
    
    for char_name, char_state in game_state.characters.items():
        budget = char_state.private_info.get_current_budget(game_state.current_date)
        assets = char_state.private_info.true_asset_balance
        
        message += f"\n{char_name}:\n"
        message += f"  Budget: ${budget:,.0f}\n"
        message += f"  Assets:\n"
        message += f"    - Technical Capability: {assets.technical_capability:.1f}\n"
        message += f"    - Capital: ${assets.capital:,.0f}\n"
        message += f"    - Human Resources: {assets.human:.1f}\n"
        
        active_projects = [p for p in char_state.private_info.projects if p.status == "active"]
        completed_projects = [p for p in char_state.private_info.projects if p.status == "completed"]
        
        message += f"  Active Projects: {len(active_projects)}\n"
        for project in active_projects:
            message += f"    - {project.name}: {project.progress*100:.0f}% complete\n"
        
        if completed_projects:
            message += f"  Completed Projects: {len(completed_projects)}\n"
            for project in completed_projects:
                message += f"    - {project.name}\n"
    
    logger.log(log_level, message)

