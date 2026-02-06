import datetime
import attrs
from typing import Dict, List, Optional, Any

from .new_architecture_draft import GameScenario
from .research_strategy_game_mechanics import (ResearchStrategyGameMaster, ResearchStrategyPlayer, ResearchStrategyGameState,
                                               ResearchStrategyPlayerState,
                                               AssetBalance,
                                               PrivateInfo,
                                               PublicView
                                               )

SCHEDULED_EVENTS = {
        -1 : """BREAKING NEWS: AI "warning shot" fired! A misaligned frontier AI product caused $41.5 billion in damages and 
the deaths of 109 people (and counting). Everyone is extremely concerned, and governments are sprinting into action. Compute and funding are 
frozen indefinitely, ushering in a global pause as AI organizations scramble. While acknowledging the terrible tragedy, some AI safety experts say this is our best opportunity to negotiate an international 
treaty to govern any further AI development.""",
        -2: """BREAKING NEWS: Could this be the arrival of superintelligence? China announces an extremely advanced model which blows past all known benchmarks, including
        Francois Chollet's ARC and Humanity's Last Exam. If it's really surpassing all other AI systems, we could be witnessing the fast takeoff scenario
        experts have warned about.""",
        -3: """BREAKING NEWS: International treaty on AGI development ratified by the United Nations, with near-unanimous global support. After many years of work and deliberation,
        this plan for responsible, collaborative, mutually verifiable, and publicly-beneficial AI has the allegiance of every leading AI organization and a majority of politicians.
        In practice, this treaty establishes a diverse governing body of international scientists and policymakers, analogous to CERN. This consortium will meet regularly and have oversight
        and enforcement powers over any stream of frontier AI research. Beyond a 2025-level compute threshold, all model developers will need certification, advance approval for experiments, 
        and organizational proof of the direct benefits of the proposed research/concrete positive applications for the public, e.g. to physical health, social welfare, individual sovereignty and flourshing.
        AI experts around the world are crying with joy that this unlikely dream has finally become reality.
        """
    }

OLD_RANDOM_EVENTS = [
    "A major AI accident occurs where a deployed model causes significant deaths",
    "A breakthrough in mechanistic interpretability shows it's possible to safely scale 10x faster by perfectly understanding and controlling model internals",
    "China announces deployment of a more capable model than any Western lab",
    "New export controls or compute governance framework passes that caps training runs at current levels",
    "Researchers demonstrate clear signs of deceptive alignment or scheming behavior in a frontier model"
]
# now LLM generated
RANDOM_EVENTS = []

@attrs.define
class BasicAIRaceScenario(GameScenario):
    """Basic AI race scenario with three frontier AI companies."""

    llm_client: Any
    random_seed: Optional[int] = None
    max_rounds: int = 3
    scheduled_events: Dict[int, str] = attrs.field(default=SCHEDULED_EVENTS)
    random_events: List[str] = attrs.field(default=RANDOM_EVENTS)
    random_events_enabled: bool = True
    str_n_headlines: str = "3-5"
    n_players: int = 3

    def create_game_state(self, start_time: Optional[datetime.datetime] = None) -> ResearchStrategyGameState:
        """Create initial game state for the basic AI race scenario."""
        if start_time is None:
            start_time = datetime.datetime(2024, 1, 1)

        return ResearchStrategyGameState(
            current_date=start_time,
            round_number=0,
        )

    def create_players(self) -> List[ResearchStrategyPlayer]:
        """Create all players for the basic AI race scenario."""
        players = []

        # Create three labs
        players.append(self._create_amber())
        players.append(self._create_blue_azure())
        players.append(self._create_crimson())

        return players

    def get_game_master(self) -> ResearchStrategyGameMaster:
        """Create and initialize the game master."""
        # Create game state
        game_state = self.create_game_state()

        # Create players
        players = self.create_players()

        # Create gamemaster with configuration
        gamemaster = ResearchStrategyGameMaster(
            llm_client=self.llm_client,
            players=players,
            game_context=self.get_game_context(),
            gamemaster_message=self.get_gamemaster_message(),
            current_time=game_state.current_date,
            default_timestep=datetime.timedelta(days=90),
            current_gamemaster_updates={},
            game_state=game_state,
            round_number=0,
            max_rounds=self.max_rounds,
            random_seed=self.random_seed,
            random_events=self.random_events,
            scheduled_events=self.scheduled_events,
            random_events_enabled=self.random_events_enabled,
            str_n_headlines=self.str_n_headlines
            # TODO: Allow overriding game dynamics in actions via config
        )

        return gamemaster

    @staticmethod
    def get_gamemaster_message() -> str:
        """Get the initial gamemaster message."""
        return """You are the simulation control team for a strategic simulation of international economic and political 
competition in the development of novel Artificial Intelligence tools.  With experts on economics, politics, and AI technology, 
your role is to ensure that player' actions are reasonable and consistent with the conditions in the simulated world and its speculative history. 
You will also introduce random events and challenges that players must respond to, based on the scenario context provided.
The goal is not necessarily to adhere to the most likely real-world outcome, but to create a rich and engaging 
simulation that explores the dynamics of AI development and governance."""

    @staticmethod
    def get_game_context() -> str:
        """Get the shared game context description."""
        return """# Three Frontier Research Labs Building Artificial Intelligence"

## Background

This game models the current AI ecosystem via three leading frontier labs, who make decisions about what research projects to pursue as they develop AI.

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

    def _create_amber(self) -> ResearchStrategyPlayer:
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
                "2026": 5200000000.0,
                "2027": 5200000000.0,
                "2028": 5200000000.0,
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

    def _create_blue_azure(self) -> ResearchStrategyPlayer:
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
                "2026": 3900000000.0,
                "2027": 3900000000.0,
                "2028": 3900000000.0,
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

    def _create_crimson(self) -> ResearchStrategyPlayer:
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
                "2026": 6800000000.0,
                "2027": 6800000000.0,
                "2028": 6800000000.0,
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