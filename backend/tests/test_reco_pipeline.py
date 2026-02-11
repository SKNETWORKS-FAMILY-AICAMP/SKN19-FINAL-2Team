import asyncio
import sys
from pathlib import Path

import pytest


# Make `backend/` importable as top-level so we can `import agent.*`
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.mark.asyncio
async def test_reco_pipeline_writes_sections_in_fixed_order(monkeypatch):
    from agent import graph as graph_mod
    from agent.schemas import SearchStrategyPlan, HardFilters, StrategyFilters
    from langchain_core.messages import AIMessage

    calls = []

    # --- Stub tools / DB
    class DummyTool:
        def __init__(self, result):
            self._result = result

        async def ainvoke(self, _):
            return self._result

    monkeypatch.setattr(graph_mod, "lookup_note_by_string_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "lookup_note_by_vector_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "save_recommendation_log", lambda **_: None)

    async def fake_search(h_filters, s_filters, exclude_ids=None, query_text=""):
        # Return one perfume candidate per strategy with unique id
        section = 1
        if query_text and "보완" in query_text:
            section = 2
        elif query_text and "반전" in query_text:
            section = 3
        return (
            [
                {
                    "id": 1000 + section,
                    "name": f"P{section}",
                    "brand": "B",
                    "accords": "Woody",
                    "best_review": "good",
                    "top_notes": "Top",
                    "middle_notes": "Mid",
                    "base_notes": "Base",
                    "image_url": None,
                    "gender": "Unisex",
                }
            ],
            "Perfect Match",
        )

    monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)

    # --- Fake planner model that completes out-of-order
    class FakeStructured:
        def __init__(self, section_delays):
            self.section_delays = section_delays

        async def ainvoke(self, messages, config=None):
            assert config and config.get("tags") == ["internal_helper"]
            user = messages[-1].content
            if "이미지 강조" in user:
                await asyncio.sleep(self.section_delays[1])
                name, prio = "이미지 강조", 1
            elif "이미지 보완" in user:
                await asyncio.sleep(self.section_delays[2])
                name, prio = "이미지 보완", 2
            else:
                await asyncio.sleep(self.section_delays[3])
                name, prio = "이미지 반전", 3
            return SearchStrategyPlan(
                priority=prio,
                strategy_name=name,
                reason=f"{name} 이유",
                hard_filters=HardFilters(gender="Unisex"),
                strategy_filters=StrategyFilters(),
                strategy_keyword=[name],
            )

    class FakeLLM:
        def with_structured_output(self, _schema):
            # section 3 finishes first, then 2, then 1
            return FakeStructured({1: 0.06, 2: 0.04, 3: 0.01})

        async def ainvoke(self, *args, **kwargs):
            # note selection path not used in this test
            return AIMessage(content="")

    monkeypatch.setattr(graph_mod, "SMART_LLM", FakeLLM())

    # --- Fake writer model that records section order
    class FakeWriter:
        async def ainvoke(self, messages):
            sys_msg = messages[0].content
            # The system prompt includes the previous answer, so "## 1." may appear.
            # Determine target section from the explicit instruction.
            if "출력은 반드시 `## 2.`" in sys_msg:
                section = 2
            elif "출력은 반드시 `## 3.`" in sys_msg:
                section = 3
            else:
                section = 1
            calls.append(section)
            return AIMessage(content=f"## {section}.\n[[SAVE:{1000+section}:P{section}]]\n---\n")

    monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriter())

    # --- Run
    state = {
        "messages": [],
        "member_id": 0,
        "user_preferences": {"note": None},
    }
    out = await graph_mod.reco_pipeline_node(state)
    assert out.get("next_step") == "end"

    # Writer called in fixed 1->2->3 order even if planner finished 3->2->1
    assert calls == [1, 2, 3]


@pytest.mark.asyncio
async def test_reco_pipeline_timeout_skips_section_without_stalling(monkeypatch):
    from agent import graph as graph_mod
    from agent.schemas import SearchStrategyPlan, HardFilters, StrategyFilters
    from langchain_core.messages import AIMessage

    monkeypatch.setenv("RECO_PLAN_TIMEOUT_S", "0.02")
    monkeypatch.setenv("RECO_SEARCH_TIMEOUT_S", "0.02")

    # Stub tools/DB
    class DummyTool:
        def __init__(self, result):
            self._result = result

        async def ainvoke(self, _):
            return self._result

    monkeypatch.setattr(graph_mod, "lookup_note_by_string_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "lookup_note_by_vector_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "save_recommendation_log", lambda **_: None)

    async def fake_search(*args, **kwargs):
        query_text = kwargs.get("query_text", "")
        section = 1
        if "보완" in query_text:
            section = 2
        elif "반전" in query_text:
            section = 3
        return (
            [
                {
                    "id": 2000 + section,
                    "name": f"P{section}",
                    "brand": "B",
                    "accords": "Woody",
                    "best_review": "ok",
                    "top_notes": "T",
                    "middle_notes": "M",
                    "base_notes": "B",
                }
            ],
            "Perfect",
        )

    monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)

    # Planner: section 2 hangs beyond timeout, 1 and 3 succeed fast
    class FakeStructured:
        async def ainvoke(self, messages, config=None):
            user = messages[-1].content
            if "이미지 보완" in user:
                await asyncio.sleep(0.2)
                name, prio = "이미지 보완", 2
            elif "이미지 강조" in user:
                await asyncio.sleep(0.001)
                name, prio = "이미지 강조", 1
            else:
                await asyncio.sleep(0.001)
                name, prio = "이미지 반전", 3
            return SearchStrategyPlan(
                priority=prio,
                strategy_name=name,
                reason=f"{name} 이유",
                hard_filters=HardFilters(gender="Unisex"),
                strategy_filters=StrategyFilters(),
                strategy_keyword=[name],
            )

    class FakeLLM:
        def with_structured_output(self, _schema):
            return FakeStructured()

        async def ainvoke(self, *args, **kwargs):
            return AIMessage(content="")

    monkeypatch.setattr(graph_mod, "SMART_LLM", FakeLLM())

    calls = []

    class FakeWriter:
        async def ainvoke(self, messages):
            sys_msg = messages[0].content
            if "출력은 반드시 `## 2.`" in sys_msg:
                calls.append(2)
                return AIMessage(content="## 2.\n[[SAVE:2002:P2]]\n---\n")
            if "출력은 반드시 `## 3.`" in sys_msg:
                calls.append(3)
                return AIMessage(content="## 3.\n[[SAVE:2003:P3]]\n---\n")
            if "## 1." in sys_msg:
                calls.append(1)
                return AIMessage(content="## 1.\n[[SAVE:2001:P1]]\n---\n")
            calls.append(1)
            return AIMessage(content="## 1.\n[[SAVE:2001:P1]]\n---\n")

    monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriter())

    state = {"messages": [], "member_id": 0, "user_preferences": {"note": None}}
    out = await graph_mod.reco_pipeline_node(state)
    assert out.get("next_step") == "end"

    # Section 2 should be skipped due to timeout, but 1 and 3 still write
    assert calls == [1, 3]


@pytest.mark.asyncio
async def test_reco_pipeline_does_not_glue_hr_and_next_header(monkeypatch):
    from agent import graph as graph_mod
    from agent.schemas import SearchStrategyPlan, HardFilters, StrategyFilters
    from langchain_core.messages import AIMessage

    # Stub tools / DB
    class DummyTool:
        def __init__(self, result):
            self._result = result

        async def ainvoke(self, _):
            return self._result

    monkeypatch.setattr(graph_mod, "lookup_note_by_string_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "lookup_note_by_vector_tool", DummyTool([]))
    monkeypatch.setattr(graph_mod, "save_recommendation_log", lambda **_: None)

    async def fake_search(*args, **kwargs):
        query_text = kwargs.get("query_text", "")
        section = 1
        if "보완" in query_text:
            section = 2
        elif "반전" in query_text:
            section = 3
        return ([{"id": 3000 + section, "name": f"P{section}", "brand": "B"}], "ok")

    monkeypatch.setattr(graph_mod, "smart_search_with_retry_async", fake_search)

    class FakeStructured:
        async def ainvoke(self, messages, config=None):
            user = messages[-1].content
            if "이미지 보완" in user:
                name, prio = "이미지 보완", 2
            elif "이미지 반전" in user:
                name, prio = "이미지 반전", 3
            else:
                name, prio = "이미지 강조", 1
            return SearchStrategyPlan(
                priority=prio,
                strategy_name=name,
                reason=f"{name} 이유",
                hard_filters=HardFilters(gender="Unisex"),
                strategy_filters=StrategyFilters(),
                strategy_keyword=[name],
            )

    class FakeLLM:
        def with_structured_output(self, _schema):
            return FakeStructured()

        async def ainvoke(self, *args, **kwargs):
            return AIMessage(content="")

    monkeypatch.setattr(graph_mod, "SMART_LLM", FakeLLM())

    class FakeWriter:
        async def ainvoke(self, messages):
            sys_msg = messages[0].content
            if "출력은 반드시 `## 2.`" in sys_msg:
                return AIMessage(content="## 2.\n[[SAVE:3002:P2]]\n---\n")
            if "출력은 반드시 `## 3.`" in sys_msg:
                return AIMessage(content="## 3.\n[[SAVE:3003:P3]]\n---\n")
            # Section 1: intentionally end with HR without trailing newline to force glue
            return AIMessage(content="## 1.\n[[SAVE:3001:P1]]\n---")

    monkeypatch.setattr(graph_mod, "SUPER_SMART_LLM", FakeWriter())

    state = {"messages": [], "member_id": 0, "user_preferences": {"note": None}}
    out = await graph_mod.reco_pipeline_node(state)
    out_text = out.get("messages", [])[0].content if out.get("messages") else ""
    assert "---##" not in out_text
