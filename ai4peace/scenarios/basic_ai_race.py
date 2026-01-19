"""Drone arms control scenario implementation."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import Scenario
from ..core.game_state import (
    GameState,
    CharacterState,
    AssetBalance,
    PrivateInfo,
    PublicView,
)
from ..core.actions import ActionType


# Research topics available in the game
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

class BasicAIRaceScenario(Scenario):
    """Basic AI race scenario with three frontier AI companies to start"""
    
    def create_game_state(self, start_date: Optional[datetime] = None) -> GameState:
        """Create initial game state for the basic AI race scenario."""
        if start_date is None:
            # note: is it possible this will literally matter? shall we start in 2027?
            # certainly the models have contextual awareness
            start_date = datetime(2024, 1, 1)
        
        game_state = GameState(
            current_date=start_date,
            round_number=0,
            characters={},
        )
        
        # Create characters
        characters = self.create_characters()
        for char in characters:
            game_state.add_character(char)
        
        return game_state


    def create_characters(self) -> List[CharacterState]:
        """Create all characters for the drone arms control scenario."""
        characters = []
        
        # create three labs
        characters.append(create_amber())
        characters.append(create_blue_azure())
        characters.append(create_crimson())
        
        return characters

    def get_research_topics(self) -> List[Dict]:
        """Get list of available research topics."""
        return RESEARCH_TOPICS

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

def create_amber() -> CharacterState:
    """Create Amber Systems AI character: middle path between research & commercial reality """
    name = ""
    
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
        stated_objectives="Developing cost-effective drone solutions for defensive operations",
        stated_strategy="Rapid deployment of proven technologies with Western support",
        public_artifacts=[""],
    )
    
    return CharacterState(
        name=name,
        private_info=private_info,
        public_view=public_view,
    )


def create_blue_azure() -> CharacterState:
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
        stated_objectives="Developing next-generation autonomous defense systems for US and allied forces",
        stated_strategy="Technology leadership through significant R&D investment and strategic partnerships",
        public_artifacts=["Lattice platform", "Autonomous surveillance systems", "Military contracts"],
    )
    
    return CharacterState(
        name=name,
        private_info=private_info,
        public_view=public_view,
    )


def create_us_government() -> CharacterState:
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
    
    return CharacterState(
        name=name,
        private_info=private_info,
        public_view=public_view,
    )


def create_russian_government() -> CharacterState:
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
    
    return CharacterState(
        name=name,
        private_info=private_info,
        public_view=public_view,
    )


def create_iranian_manufacturer() -> CharacterState:
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
    
    return CharacterState(
        name=name,
        private_info=private_info,
        public_view=public_view,
    )


# Convenience functions for backwards compatibility
def create_game_state(start_date: datetime = None) -> GameState:
    """Create game state using the scenario."""
    scenario = DroneArmsControlScenario()
    return scenario.create_game_state(start_date)


def create_characters() -> List[CharacterState]:
    """Create characters using the scenario."""
    scenario = DroneArmsControlScenario()
    return scenario.create_characters()


def get_game_context() -> str:
    """Get game context using the scenario."""
    scenario = DroneArmsControlScenario()
    return scenario.get_game_context()


def get_research_topics() -> List[Dict]:
    """Get research topics using the scenario."""
    scenario = DroneArmsControlScenario()
    return scenario.get_research_topics()

