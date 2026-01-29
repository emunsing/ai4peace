"""ResearchStrategy scenario implementations using the new architecture."""

import datetime
from typing import Dict, List, Optional, Any

from .new_architecture_draft import GameScenario
from .research_strategy_game_mechanics import (ResearchStrategyGameMaster, ResearchStrategyPlayer, ResearchStrategyGameState,
                                               ResearchStrategyPlayerState,
                                               AssetBalance,
                                               PrivateInfo,
                                               PublicView
                                               )



class DroneArmsControlScenario(GameScenario):
    """Drone arms control scenario implementation."""
    
    def __init__(
        self,
        llm_client: Any,
        random_seed: Optional[int] = None,
        **kwargs  # Allow additional configuration
    ):
        """Initialize the scenario."""
        self.llm_client = llm_client
        self.random_seed = random_seed
        self.config = kwargs

    
    def create_game_state(self, start_time: Optional[datetime.datetime] = None) -> ResearchStrategyGameState:
        """Create initial game state for the drone arms control scenario."""
        if start_time is None:
            start_time = datetime.datetime(2024, 1, 1)
        
        return ResearchStrategyGameState(
            current_date=start_time,
            round_number=0,
        )
    
    def create_players(self) -> List[ResearchStrategyPlayer]:
        """Create all players for the drone arms control scenario."""
        players = []
        
        # Ukraine/EU/Western characters
        players.append(self._create_ukrainian_startup())
        players.append(self._create_anduril())
        players.append(self._create_us_government())
        
        # Russian/Iranian characters
        players.append(self._create_russian_government())
        players.append(self._create_iranian_manufacturer())
        
        return players
    
    def get_game_master(self) -> ResearchStrategyGameMaster:
        """Create and initialize the game master."""
        game_state = self.create_game_state()
        players = self.create_players()
        
        gamemaster = ResearchStrategyGameMaster(
            players=players,
            current_time=game_state.current_date,
            default_timestep=datetime.timedelta(days=90),
            current_gamemaster_updates={},
            game_state=game_state,
            round_number=0,
            random_seed=self.random_seed,
            random_events=[],  # Can add scenario-specific events
            # TODO: more examples of how best to override config
        )
        
        return gamemaster
    
    def get_game_context(self) -> str:
        """Get the shared game context description."""
        return """# International Technology Policy Simulation: Arms Control on Autonomous Drones

## Background

This simulation models the development and potential regulation of autonomous drone technologies in the context of international conflict and arms control. The scenario is set against the backdrop of:

- The ongoing Russia-Ukraine conflict
- Potential future Western-Russian conflicts
- Potential future US-China conflicts
- Evolving international norms around autonomous weapons systems

## Arms Control Proposal

A proposed arms control framework aims to prevent the development of fully autonomous systems capable of indiscriminate targeting of civilians without human intervention. This would affect:

- Systems that can autonomously select and engage targets
- Systems operating beyond human oversight
- Technologies that could enable autonomous targeting at scale

## Current Situation

- Ukraine is actively using drone technology in ongoing conflict
- Western companies and governments are developing advanced autonomous systems
- Russian and Iranian entities are developing and deploying their own drone capabilities
- International discussions about regulation are ongoing but not yet binding

## Game Mechanics

- Each round represents approximately 3 months
- Characters can take multiple actions per round
- Research projects take time and resources to complete
- Information asymmetry: each character has private information not fully visible to others
- Characters can engage in diplomacy, espionage, and public campaigns

## Victory Conditions

This is an open-ended simulation. Success is measured by:
- Achievement of stated objectives
- Technological advancement
- Resource accumulation
- Influence on policy outcomes
- Strategic positioning for future conflicts"""
    
    def _create_ukrainian_startup(self) -> ResearchStrategyPlayer:
        """Create Ukrainian drone startup character."""
        name = "Ukrainian Drone Startup"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=15.0,
                capital=500000.0,
                human=25.0,
            ),
            objectives="""Your primary objective is to support Ukraine's defense capabilities by developing effective drone technologies. You are motivated by the ongoing war and the urgent need for battlefield innovations. You seek to:
1. Develop practical, battlefield-tested drone systems
2. Secure funding from Western partners (EU, US, NATO)
3. Rapidly deploy technologies that can make an immediate impact
4. Maintain operational independence while leveraging partnerships""",
            strategy="""Focus on rapid iteration and practical solutions. Prioritize short-term tactical advantages. Seek partnerships with Western companies for funding and technology transfer. Emphasize the defensive nature of your work.""",
            budget={
                "2024": 2000000.0,
                "2025": 3000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=12.0,  # Slightly understated
                capital=400000.0,
                human=20.0,
            ),
            stated_objectives="Developing cost-effective drone solutions for defensive operations",
            stated_strategy="Rapid deployment of proven technologies with Western support",
            public_artifacts=["Battlefield-proven reconnaissance drones"],
        )
        
        player_state = ResearchStrategyPlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return ResearchStrategyPlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_anduril(self) -> ResearchStrategyPlayer:
        """Create Anduril Industries character."""
        name = "Anduril Industries"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=85.0,
                capital=50000000.0,
                human=500.0,
            ),
            objectives="""Your objectives as a leading defense technology company:
1. Develop cutting-edge autonomous systems for military applications
2. Secure contracts with US and allied governments
3. Build profitable defense technology business
4. Advance the state-of-the-art in AI-powered defense systems
5. Navigate regulatory landscape for autonomous weapons""",
            strategy="""Leverage significant technical capabilities and capital. Focus on high-value contracts. Develop systems that can be exported to allies. Balance innovation with regulatory compliance. Use lobbying to shape favorable policy.""",
            budget={
                "2024": 100000000.0,
                "2025": 120000000.0,
                "2026": 140000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=80.0,
                capital=45000000.0,
                human=450.0,
            ),
            stated_objectives="Developing next-generation autonomous defense systems for US and allied forces",
            stated_strategy="Technology leadership through significant R&D investment and strategic partnerships",
            public_artifacts=["Lattice platform", "Autonomous surveillance systems", "Military contracts"],
        )
        
        player_state = ResearchStrategyPlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return ResearchStrategyPlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_us_government(self) -> ResearchStrategyPlayer:
        """Create US Government character."""
        name = "US Government (DoD)"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=95.0,
                capital=1000000000.0,
                human=10000.0,
            ),
            objectives="""Your objectives as the US Department of Defense:
1. Maintain technological superiority over adversaries
2. Support Ukraine while avoiding direct conflict escalation
3. Develop capabilities to counter Russian and Chinese threats
4. Navigate arms control negotiations while preserving options
5. Ensure compliance with existing treaties and international law""",
            strategy="""Use significant resources to maintain advantage. Support allies through technology transfer and funding. Engage in arms control negotiations from a position of strength. Develop capabilities that can serve multiple purposes (deterrence, defense, offense).""",
            budget={
                "2024": 2000000000.0,
                "2025": 2100000000.0,
                "2026": 2200000000.0,
                "2027": 2300000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=90.0,
                capital=900000000.0,
                human=9000.0,
            ),
            stated_objectives="Ensuring national security through technological innovation and international cooperation",
            stated_strategy="Balanced approach combining defensive capabilities with diplomatic engagement",
            public_artifacts=["Defense budgets", "Military procurement announcements", "Policy statements"],
        )
        
        player_state = ResearchStrategyPlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return ResearchStrategyPlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_russian_government(self) -> ResearchStrategyPlayer:
        """Create Russian Government character."""
        name = "Russian Government (Ministry of Defense)"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=70.0,
                capital=800000000.0,
                human=8000.0,
            ),
            objectives="""Your objectives:
1. Develop autonomous drone capabilities to gain battlefield advantage
2. Counter Western technological superiority
3. Support ongoing military operations
4. Maintain technological parity or advantage where possible
5. Evade or work around potential arms control restrictions""",
            strategy="""Leverage existing industrial base and partnerships (especially with Iran). Focus on rapid deployment over perfect technology. Use asymmetric approaches. Invest in capabilities that can counter Western systems. Minimize dependency on Western technology.""",
            budget={
                "2024": 1500000000.0,
                "2025": 1600000000.0,
                "2026": 1700000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=65.0,
                capital=750000000.0,
                human=7500.0,
            ),
            stated_objectives="Ensuring defense capabilities through indigenous technology development",
            stated_strategy="Self-reliance and strategic partnerships for defense technology",
            public_artifacts=["Military equipment displays", "State media announcements"],
        )
        
        player_state = ResearchStrategyPlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return ResearchStrategyPlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_iranian_manufacturer(self) -> ResearchStrategyPlayer:
        """Create Iranian drone manufacturer character."""
        name = "Iranian Drone Manufacturer"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=50.0,
                capital=30000000.0,
                human=300.0,
            ),
            objectives="""Your objectives:
1. Develop and export drone technologies
2. Support allied nations (Russia, proxies) with drone capabilities
3. Build technological capabilities despite sanctions
4. Generate revenue through exports
5. Advance domestic defense technology base""",
            strategy="""Focus on cost-effective solutions. Leverage partnerships with Russia for technology and markets. Prioritize systems that are effective despite lower sophistication. Use exports to fund further development. Work around sanctions through various channels.""",
            budget={
                "2024": 50000000.0,
                "2025": 55000000.0,
                "2026": 60000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=45.0,
                capital=25000000.0,
                human=250.0,
            ),
            stated_objectives="Developing and exporting defense technology for legitimate defense purposes",
            stated_strategy="Innovation through indigenous development and strategic partnerships",
            public_artifacts=["Export announcements", "Technology demonstrations"],
        )
        
        player_state = ResearchStrategyPlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return ResearchStrategyPlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )

