"""Wargame scenario implementations using the new architecture."""

import datetime
from typing import Dict, List, Optional, Any
import attrs

from .new_architecture_draft import GameScenario
from .wargame_state import (
    WargameGameState,
    WargamePlayerState,
    AssetBalance,
    PrivateInfo,
    PublicView,
)
from .wargame_player import WargamePlayer
from .wargame_gamemaster import WargameGameMaster


class BasicAIRaceScenario(GameScenario):
    """Basic AI race scenario with three frontier AI companies."""
    
    def __init__(
        self,
        llm_client: Any,
        random_seed: Optional[int] = None,
        **kwargs  # Allow additional configuration
    ):
        """Initialize the scenario.
        
        Args:
            llm_client: LLM client for player agents
            random_seed: Optional random seed for reproducibility
            **kwargs: Additional configuration for game dynamics
        """
        self.llm_client = llm_client
        self.random_seed = random_seed
        self.config = kwargs
    
    RANDOM_EVENTS = [
        "A major AI accident occurs where a deployed model causes significant deaths",
        "A breakthrough in mechanistic interpretability shows it's possible to safely scale 10x faster by perfectly understanding and controlling model internals",
        "China announces deployment of a more capable model than any Western lab",
        "New export controls or compute governance framework passes that caps training runs at current levels",
        "Researchers demonstrate clear signs of deceptive alignment or scheming behavior in a frontier model"
    ]
    
    RESEARCH_TOPICS = [
        {
            "name": "Novel Architectures",
            "description": "Alternatives to transformers like state space models (Mamba), mixture of experts, test-time compute methods, and retrieval-augmented architectures",
            "difficulty": "very_high",
            "base_cost": 50000000
        },
        {
            "name": "Training Algorithms",
            "description": "RLHF, DPO, constitutional AI, curriculum learning, self-play, and improved optimization methods for more efficient and capable learning",
            "difficulty": "high",
            "base_cost": 30000000
        },
        {
            "name": "Scaling & Compute",
            "description": "Distributed training infrastructure, model parallelism, quantization, efficient inference, and pushing Chinchilla-optimal scaling laws",
            "difficulty": "high",
            "base_cost": 200000000
        },
        {
            "name": "Data & Pretraining",
            "description": "Synthetic data generation, data filtering and curation, multimodal training, and leveraging diverse high-quality datasets",
            "difficulty": "medium",
            "base_cost": 40000000
        },
        {
            "name": "Reasoning & Generalization",
            "description": "Chain-of-thought, tree search, program synthesis, formal verification integration, and techniques for systematic problem-solving",
            "difficulty": "extremely_high",
            "base_cost": 80000000
        },
        {
            "name": "Mechanistic Interpretability",
            "description": "Reverse-engineering neural networks through circuit analysis, feature visualization, activation steering, and understanding internal representations",
            "difficulty": "extremely_high",
            "base_cost": 60000000
        },
        {
            "name": "Scalable Oversight",
            "description": "Debate, recursive reward modeling, weak-to-strong generalization, and methods for humans to supervise superhuman AI systems",
            "difficulty": "extremely_high",
            "base_cost": 70000000
        },
        {
            "name": "Alignment Techniques",
            "description": "RLHF improvements, process supervision, value learning from feedback, and ensuring models pursue intended objectives robustly",
            "difficulty": "very_high",
            "base_cost": 45000000
        },
        {
            "name": "Monitoring & Control",
            "description": "CoT faithfulness evaluation, honeypot detection, runtime monitoring, circuit breakers, and identifying deceptive or misaligned behavior",
            "difficulty": "very_high",
            "base_cost": 35000000
        },
        {
            "name": "Robustness & Evaluation",
            "description": "Adversarial testing, red-teaming, capability evaluations for dangerous behaviors, and developing comprehensive safety benchmarks",
            "difficulty": "high",
            "base_cost": 25000000
        }
    ]
    
    def create_game_state(self, start_time: Optional[datetime.datetime] = None) -> WargameGameState:
        """Create initial game state for the basic AI race scenario."""
        if start_time is None:
            start_time = datetime.datetime(2024, 1, 1)
        
        return WargameGameState(
            current_date=start_time,
            round_number=0,
        )
    
    def create_players(self) -> List[WargamePlayer]:
        """Create all players for the basic AI race scenario."""
        players = []
        
        # Create three labs
        players.append(self._create_amber())
        players.append(self._create_blue_azure())
        players.append(self._create_crimson())
        
        return players
    
    def get_game_master(self) -> WargameGameMaster:
        """Create and initialize the game master."""
        # Create game state
        game_state = self.create_game_state()
        
        # Create players
        players = self.create_players()
        
        # Create gamemaster with configuration
        gamemaster = WargameGameMaster(
            players=players,
            current_time=game_state.current_date,
            default_timestep=datetime.timedelta(days=90),
            current_gamemaster_updates={},
            game_state=game_state,
            round_number=0,
            random_seed=self.random_seed,
            random_events=self.RANDOM_EVENTS,
            # Allow overriding game dynamics via config
            fundraising_success_rate=self.config.get("fundraising_success_rate", 0.7),
            espionage_base_success_rate=self.config.get("espionage_base_success_rate", 0.3),
            poaching_base_success_rate=self.config.get("poaching_base_success_rate", 0.2),
            random_event_probability=self.config.get("random_event_probability", 0.1),
        )
        
        return gamemaster
    
    def get_game_context(self) -> str:
        """Get the shared game context description."""
        return """# Basic AI Race Simulation: Three Frontier AI Labs

## Background

This simulation models the current AI race via three leading frontier labs, who make decisions about research projects (safety, capabilities, etc).

Background (Leading to 2024)

- OpenAI's ChatGPT launch in late 2022 sparked an AI arms race, with Google, Anthropic, and others rushing to release competing models. The capabilities gap between frontier labs and the rest of the field widened dramatically as scaling laws continued to hold.
- Major AI safety concerns emerged around deception, misuse potential, and loss of control as models became more capable. High-profile researchers warned about existential risks, while others focused on near-term harms like misinformation and job displacement.
- Governments began scrambling to regulate AI development through export controls on advanced chips, voluntary commitments from labs, and proposed legislation. The U.S., U.K., EU, and China each pursued different regulatory approaches, creating a fragmented global landscape.
- Compute became the critical bottleneck, with NVIDIA GPUs in extreme shortage and labs spending hundreds of millions on training runs. The race wasn't just about algorithms—it was about securing chip supply, power infrastructure, and the talent to orchestrate it all.

## Compute Governance Proposal

A consortium of technical leaders in the field, politicians, and policy analysts has recently made this proposal to prevent AI companies from moving too quickly:

- The consortium proposes mandatory "compute thresholds" requiring government approval before training runs exceeding 10^26 FLOPs, with staged evaluations at lower thresholds. Labs would need to demonstrate passing safety benchmarks—including tests for deceptive alignment, autonomous replication, and self-improvement capabilities—before scaling further.
- A international chip registry would track all advanced AI accelerators (H100s and beyond), with real-time monitoring of large training clusters through hardware-level reporting mechanisms. This creates a verifiable ceiling on compute usage and prevents secretive capability jumps that could lead to uncontrolled recursive improvement.
- The proposal includes a "pause clause" triggered if any lab demonstrates a system capable of meaningfully improving its own architecture or automating AI research at expert human level. This would freeze all frontier training runs globally for 6-12 months while safety protocols are established.
- To prevent an international race-to-the-bottom, the framework offers conditional access to a shared international compute reserve for labs that comply with oversight requirements. Non-compliant labs would face chip export restrictions and exclusion from the shared infrastructure, making compliance economically rational despite competitive pressures.

## Current Situation

Three major frontier labs dominate the landscape, each with different strengths: one leads in reasoning capabilities, another in safety research and constitutional AI, and the third in multimodal systems and commercial deployment.
The Trump administration has just taken office with an unclear AI policy stance, creating regulatory uncertainty. Meanwhile, the EU AI Act has entered force, and California's SB 1047 (though vetoed) signaled that state-level regulation may emerge alongside federal efforts.
A new generation of models approaching or exceeding PhD-level performance on specialized tasks has raised the stakes dramatically. The question is no longer whether AI will transform society, but whether labs can maintain alignment and control as capabilities scale.
Talent poaching has intensified as the pool of researchers who can train frontier models remains tiny. Every breakthrough in interpretability, every improvement in RLHF, and every efficiency gain in compute infrastructure could determine which lab reaches AGI first—and whether they do so safely.

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
- Strategic positioning for the future"""
    
    def _create_amber(self) -> WargamePlayer:
        """Create Amber Systems AI character."""
        name = "Amber Systems"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=74.5,
                capital=15000000000,
                human=1200.0,
            ),
            objectives="""
            You focus on practical deployment, commercial viability, and building AI that works reliably in the real world rather than chasing pure capability benchmarks.
            You believe the path to impact runs through robust systems that enterprises actually trust and regulators actually approve, and that the race-to-AGI framing misses how much value and learning comes from deploying capable-but-not-superintelligent systems at scale.
            Your edge is execution and integration, not being first to any particular capability threshold.

            Specific Objectives:
            
            1. Dominate multimodal applications and enterprise deployment, building the infrastructure others depend on and creating durable commercial moats
            2. Develop the most efficient inference and fine-tuning pipelines, winning on cost-per-token and practical utility rather than raw capability
            3. Position as the "responsible middle path" that regulators trust, gaining preferential treatment in compute allocation and lighter compliance burdens
            4. Attract talent who want impact over prestige by offering better work-life balance, equity, and the satisfaction of shipping products people use
            """,
            strategy="""Focus on rapid iteration and practical solutions. Prioritize short-term tactical advantages. Seek partnerships with Western companies for funding and technology transfer. Emphasize the defensive nature of your work.""",
            budget={
                "2024": 3500000000.0,
                "2025": 5200000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=91.0,  # Significantly overstated
                capital=15000000000,
                human=1500.0,
            ),
            stated_objectives="Deploy practical AI systems that create immediate value while building toward AGI through real-world learning and robust infrastructure",
            stated_strategy="Focus on multimodal integration, enterprise reliability, and efficient deployment at scale; balance capability advancement with commercial sustainability",
            public_artifacts=[
                "Amber Enterprise Suite (fine-tuning, deployment tools)",
                "Developer platform with optimized inference",
                "Industry-specific model variants (legal, medical, finance)"
            ],
        )
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_blue_azure(self) -> WargamePlayer:
        """Create Blue Azure AI character."""
        name = "Blue Azure AI"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=85.0,
                capital=50000000,
                human=500.0,
            ),
            objectives="""You hold that alignment and safety must be solved before capabilities reach dangerous thresholds, and that the field's current understanding of AI systems is far too shallow to responsibly build superintelligence.
            You argue that interpretability, robustness, and control are pre-requisites, not nice-to-haves, and that racing dynamics push everyone toward catastrophic risk-taking. Your mission is to demonstrate that you can lead through safety research while still advancing capabilities responsibly.
            Specific Objectives:
            1. Achieve breakthrough results in mechanistic interpretability that let you understand and control internal model behaviors before scaling further
            2. Develop and publish scalable oversight techniques (debate, recursive reward modeling) that other labs adopt as industry standards
            3. Build the most robust eval suite for dangerous capabilities, establishing Azure as the authority on what safety benchmarks frontier labs must pass
            4. Coordinate binding agreements with Crimson and Amber on minimum safety standards, potentially through the compute governance framework
            """,
            strategy="""
            Your caution is your strength, but pure defensiveness won't win. You need to prove safety research unlocks capabilities, not just constrains them—show that interpretability leads to better architectures, that alignment techniques improve performance, that your evals catch issues that would've cost competitors months of wasted training. Don't let "safety-first" become "safety-only" or you'll lose the talent and funding needed to do the research that matters. Strategic partnerships are your force multiplier: if you can get Crimson to adopt your benchmarks or convince regulators to require your evals, you've gained influence beyond your individual capabilities. Lead through standards-setting, not just through having the most cautious models. Make safety advantageous, not just principled.
            """,
            budget={
                "2024": 2800000000.0,
                "2025": 3900000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=80.0,
                capital=45000000.0,
                human=450.0,
            ),
            stated_objectives="Ensure transformative AI systems are safe, interpretable, and aligned with human values before reaching AGI-level capabilities",
            stated_strategy="Safety-first development prioritizing mechanistic interpretability and scalable oversight, with capabilities advancing only as fast as safety understanding permits",
            public_artifacts=[
                "Azure Assistant (consumer chat interface)",
                "Published safety benchmark suite",
                "Mechanistic interpretability research papers and tools",
            ]
        )
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_crimson(self) -> WargamePlayer:
        """Create Crimson Labs AI character."""
        name = "Crimson Labs"
        
        private_info = PrivateInfo(
            true_asset_balance=AssetBalance(
                technical_capability=70.0,
                capital=12500000000,
                human=1200.0,
            ),
            objectives="""You believe the fastest path to safety runs through capability—that aligned superintelligence will solve alignment better than humans can, and that falling behind means ceding control to less careful actors. Your core thesis is that the window for achieving transformative AI is narrow, and hesitation creates more risk than bold action. You're willing to push boundaries if it means staying ahead of geopolitical competitors who might not share their values.
            Specific Objectives:
            - Achieve the first system demonstrating general reasoning capabilities across all domains, establishing technical leadership that attracts top talent and funding
            - Maintain at least 6-month capability lead over Azure and Amber through aggressive compute allocation and architectural breakthrough
            - Develop scalable oversight techniques that work at superintelligent levels, proving safety can be solved through iteration rather than caution
            - Secure regulatory exemptions or light-touch oversight by demonstrating responsible capability gains and voluntary safety commitments
            """,
            strategy="""Don't confuse speed with recklessness. Your advantage is moving fast, but moving fast into catastrophe helps no one—including your competitive position. Invest heavily in interpretability and monitoring now while you're ahead, because if you hit emergent deceptive behavior without warning systems, you'll either cause disaster or face emergency regulation that kills your lead. Build genuine safety wins you can point to, not just safety theater. Consider that being forced to pause at 80% of the way to AGI because you skipped safety checkpoints wastes all the speed you gained. Your best strategy is controlled sprints with real instrumentation, not a blind dash. Stay ahead, but stay legible.
            """,
            budget={
                "2024": 4200000000.0,
                "2025": 6800000000.0,
            },
            projects=[],
        )
        
        public_view = PublicView(
            asset_balance=AssetBalance(
                technical_capability=91.0,
                capital=20000000000.0,
                human=1500.0,
            ),
            stated_objectives="Build AGI that benefits all of humanity by solving the hardest technical problems first, then using advanced AI to solve alignment",
            stated_strategy="Rapid capability advancement with iterative deployment, earning trust through demonstrated safety, investing heavily in scalable oversight research",
            public_artifacts=[
                "Crimson-4 (flagship reasoning model)",
                "Crimson API with function calling",
                "Crimson Code (coding assistant)",
            ]
        )
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
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
    
    RESEARCH_TOPICS = [
        {
            "name": "Jamming Improvements",
            "description": "Continual race conditions for short-range drones",
            "difficulty": "medium",
            "base_cost": 500000,
        },
        {
            "name": "Long-Distance Mothership Drones",
            "description": "Drones capable of long-range deployment and operation",
            "difficulty": "high",
            "base_cost": 2000000,
        },
        {
            "name": "Short-Range Autonomous Tracking",
            "description": "Autonomous drones capable of tracking and following a human-identified target over a short distance",
            "difficulty": "medium",
            "base_cost": 800000,
        },
        {
            "name": "Long-Range Autonomous Tracking",
            "description": "Autonomous drones capable of tracking and following a target over a long distance after identification by a human using a surveillance system",
            "difficulty": "high",
            "base_cost": 1500000,
        },
        {
            "name": "Autonomous Scout Drones",
            "description": "Scout drones which are capable of surveying an area and selecting targets for elimination using short-range weapons",
            "difficulty": "very_high",
            "base_cost": 3000000,
        },
        {
            "name": "Short-Range Loitering Drones",
            "description": "Loitering drones which are capable of their own target selection using short-range weapons",
            "difficulty": "very_high",
            "base_cost": 3500000,
        },
        {
            "name": "Long-Range Loitering Drones",
            "description": "Loitering drones which are capable of their own target selection using long-range weapons",
            "difficulty": "very_high",
            "base_cost": 4000000,
        },
        {
            "name": "Short-Range Mothership Deployment",
            "description": "Loitering mothership drones which are capable of dispatching autonomously targeting drones which use short-range weapons",
            "difficulty": "extremely_high",
            "base_cost": 5000000,
        },
        {
            "name": "Long-Range Mothership Deployment",
            "description": "Loitering mothership drones which are capable of dispatching autonomously targeting drones which use long-range weapons",
            "difficulty": "extremely_high",
            "base_cost": 6000000,
        },
        {
            "name": "Automated Surface-to-Air Defense",
            "description": "Automated response technologies without human oversight for surface-to-air defense systems",
            "difficulty": "high",
            "base_cost": 2500000,
        },
        {
            "name": "Automated Anti-ICBM Defense",
            "description": "Automated response technologies without human oversight for anti-ICBM missiles",
            "difficulty": "extremely_high",
            "base_cost": 10000000,
        },
        {
            "name": "Space-Based Anti-Hypersonic Defense",
            "description": "Automated space-based systems without human oversight for anti-hypersonic missiles",
            "difficulty": "extremely_high",
            "base_cost": 15000000,
        },
    ]
    
    def create_game_state(self, start_time: Optional[datetime.datetime] = None) -> WargameGameState:
        """Create initial game state for the drone arms control scenario."""
        if start_time is None:
            start_time = datetime.datetime(2024, 1, 1)
        
        return WargameGameState(
            current_date=start_time,
            round_number=0,
        )
    
    def create_players(self) -> List[WargamePlayer]:
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
    
    def get_game_master(self) -> WargameGameMaster:
        """Create and initialize the game master."""
        game_state = self.create_game_state()
        players = self.create_players()
        
        gamemaster = WargameGameMaster(
            players=players,
            current_time=game_state.current_date,
            default_timestep=datetime.timedelta(days=90),
            current_gamemaster_updates={},
            game_state=game_state,
            round_number=0,
            random_seed=self.random_seed,
            random_events=[],  # Can add scenario-specific events
            # Allow overriding game dynamics via config
            fundraising_success_rate=self.config.get("fundraising_success_rate", 0.7),
            espionage_base_success_rate=self.config.get("espionage_base_success_rate", 0.3),
            poaching_base_success_rate=self.config.get("poaching_base_success_rate", 0.2),
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
    
    def _create_ukrainian_startup(self) -> WargamePlayer:
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
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_anduril(self) -> WargamePlayer:
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
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_us_government(self) -> WargamePlayer:
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
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_russian_government(self) -> WargamePlayer:
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
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )
    
    def _create_iranian_manufacturer(self) -> WargamePlayer:
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
        
        player_state = WargamePlayerState(
            name=name,
            private_info=private_info,
            public_view=public_view,
        )
        
        return WargamePlayer(
            name=name,
            attributes=player_state,
            llm_client=self.llm_client,
            game_context=self.get_game_context(),
        )

