"""Wargame-specific update message classes for the generalized game architecture."""

import datetime
from typing import Dict, List, Optional
import attrs

from .new_architecture_draft import PlayerStateUpdates, GamemasterUpdateMessage
from .wargame_state import AssetBalance, ResearchProject, Message, PublicView


@attrs.define
class WargamePlayerStateUpdates(PlayerStateUpdates):
    """Player state updates for wargame simulation.
    This includes changes to the player's state, including:
    - Budget changes
    - Asset balance changes
    - Research project updates
    - Messages received
    - Public information about other players
    - Public events
    """
    # Budget and asset changes
    budget_changes: Dict[str, float] = attrs.field(factory=dict)  # year -> delta
    asset_balance_changes: Optional[AssetBalance] = None
    
    # Research project updates
    new_projects: List[ResearchProject] = attrs.field(factory=list)
    updated_projects: List[ResearchProject] = attrs.field(factory=list)
    completed_projects: List[str] = attrs.field(factory=list)  # project names
    cancelled_projects: List[str] = attrs.field(factory=list)  # project names
    
    # Messages received
    new_messages: List[Message] = attrs.field(factory=list)
    
    # Public information about other players
    other_players_public_views: Dict[str, PublicView] = attrs.field(factory=dict)
    
    # Public events
    public_events: List[str] = attrs.field(factory=list)
    
    # Action results
    action_results: List[str] = attrs.field(factory=list)  # Descriptions of what happened
    
    # Espionage results (private information discovered)
    espionage_results: List[str] = attrs.field(factory=list)
    
    # Global game state summary
    global_summary: str = ""


@attrs.define
class WargameGamemasterUpdateMessage(GamemasterUpdateMessage):
    """Gamemaster update message for wargame simulation."""
    last_action_timestamp: datetime.datetime
    next_action_timestamp: datetime.datetime
    state_updates: WargamePlayerStateUpdates

