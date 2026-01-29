import datetime
import logging
import asyncio
import os
from typing import Optional

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import SystemMessage, RequestUsage

from ai4peace.core.simulation_runner import load_scenario_class
from ai4peace.core_v2.new_architecture_draft import GameScenario
from ai4peace.core.utils import setup_logging
from autogen_core.models import CreateResult
from typing import Any, AsyncGenerator, Dict, List, Union

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
from test_responses import AI_RACE_TEST_RESPONSES

"""
NOTE: AI_RACE_TEST_RESPONSES is a defined like:
AI_RACE_TEST_RESPONSES = {"Amber_Systems": [AMBER_ROUND_1, AMBER_ROUND_2],
                    "Blue_Azure_AI": [BLUE_ROUND_1, BLUE_ROUND_2],
                    "Crimson_Labs": [CRIMSON_ROUND_1, CRIMSON_ROUND_2],}
"""


import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class DummyLLMClient:
    """
    Scripted client for integration tests.

    - Keys in `responses_by_agent` are agent names (e.g. "Amber_Systems").
    - Values are lists of per-round assistant responses.

    The client figures out which agent is speaking by reading the `source`
    of the *system message* you pass as the first message in the task.
    (This matches your example: BaseTextChatMessage(source=clean_name, content=system_message))
    """

    def __init__(self, responses_by_agent: Dict[str, List[str]], model_info: Optional[Dict[str, Any]] = None):
        self._responses = responses_by_agent
        self._idx: Dict[str, int] = {k: 0 for k in responses_by_agent.keys()}
        self._lock = asyncio.Lock()
        self.model_info = model_info

    def _extract_agent_name(self, messages: List[Any]) -> str:
        """
        You can choose your own convention here. In your draft, the first message
        is a system message with source=clean_name (the key you want).
        """
        system_msg = messages[0]
        assert isinstance(system_msg, SystemMessage)
        for agent_name in self._responses.keys():
            if f"You are {agent_name}" in system_msg.content:
                return agent_name
        raise ValueError("Could not extract agent name from system message.")

    async def create(self, llm_messages: List[Any], **kwargs: Any):
        messages = llm_messages
        agent_name = self._extract_agent_name(messages)

        async with self._lock:
            i = self._idx[agent_name]
            scripted = self._responses[agent_name]

            if i >= len(scripted):
                raise IndexError(
                    f"Ran out of scripted responses for agent '{agent_name}'. "
                    f"Requested index {i}, but only {len(scripted)} provided."
                )

            self._idx[agent_name] += 1
            text = scripted[i]

        return CreateResult(content=text, finish_reason="stop", usage=RequestUsage(prompt_tokens=100, completion_tokens=100), cached=False)


def test_integration():
    scenario = "ai4peace.core_v2.research_strategy_scenario_basic_ai_race:BasicAIRaceScenario"
    log_file = f"v2_transcript_{datetime.datetime.now().replace(microsecond=0).isoformat()}.jsonl"

    setup_logging(log_file=log_file)

    # Load scenario
    scenario_class = load_scenario_class(scenario, must_subclass=GameScenario)

    """
    TODO: We want to replace the llm_client below with a dummy llm_client which can handle a call made through autogen_agentchat.agents.AssistantAgent called like 
    ```
    ResearchStrategyPlayer.agent.run(task=[
                        BaseTextChatMessage(source=clean_name, content=system_message),
                        BaseTextChatMessage(source=self.clean_name, content=prompt)
                    ])
    ```
    where clean_name is the key of AI_RACE_TEST_RESPONSES, and we want to return the *next* entry in the list which corresponds to that key.
    """
    llm_client = DummyLLMClient(responses_by_agent=AI_RACE_TEST_RESPONSES,
                                model_info={
                                    "family": "chat",
                                    "vision": False,
                                    "function_calling": True,
                                    "json_output": True,
                                    "structured_output": False,
                                }
                                )

    scenario_instance = scenario_class(llm_client=llm_client, max_rounds=2, random_events_enabled=False)

    gamemaster = scenario_instance.get_game_master()
    asyncio.run(gamemaster.run_simulation())

if __name__ == "__main__":
    test_integration()