"""Tests for auto_mode intent routing."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

import sys
sys.path.insert(0, "swarm-backend")

from core.intent_router import classify_intent, Intent


class TestIntentRouter:
    """Test intent classification accuracy."""

    def test_code_intent(self):
        result = classify_intent("build a new app")
        assert result.intent == Intent.CODE
        assert result.target_mode == "swarm"

    def test_fix_intent(self):
        result = classify_intent("fix the broken login")
        assert result.intent == Intent.FIX
        assert result.target_mode == "swarm"

    def test_test_intent(self):
        result = classify_intent("write unit tests")
        assert result.intent == Intent.TEST
        assert result.target_mode == "swarm"

    def test_deploy_intent(self):
        result = classify_intent("deploy to production")
        assert result.intent == Intent.DEPLOY
        assert result.target_mode == "agent"

    def test_diagram_intent(self):
        result = classify_intent("draw a flowchart")
        assert result.intent == Intent.DIAGRAM
        assert result.target_mode == "agent"

    def test_research_intent(self):
        result = classify_intent("research quantum computing")
        assert result.intent == Intent.RESEARCH
        assert result.target_mode == "agent"

    def test_mesh_intent(self):
        result = classify_intent("check sensor readings")
        assert result.intent == Intent.MESH
        assert result.target_mode == "mesh"

    def test_tool_intent(self):
        result = classify_intent("use the file tool")
        assert result.intent == Intent.TOOL
        assert result.target_mode == "swarm"

    def test_plan_intent(self):
        result = classify_intent("plan a new architecture")
        assert result.intent == Intent.PLAN
        assert result.target_mode == "plan"

    def test_default_intent(self):
        result = classify_intent("hello there")
        assert result.intent == Intent.DEFAULT
        assert result.target_mode == "ask"


async def _async_gen(*items):
    """Helper to create async generators for mocks."""
    for item in items:
        yield item


class TestAutoModeDispatch:
    """Test that auto_run dispatches to the correct mode."""

    @pytest.mark.asyncio
    async def test_dispatches_to_ask_for_default(self):
        from modes.auto_mode import auto_run
        chunks = []
        with patch("modes.auto_mode.ask") as mock_ask:
            mock_ask.return_value = _async_gen(
                type("Obj", (), {"to_json": lambda self: '{"type":"text","content":"hello"}'})()
            )
            async for chunk in auto_run("hello there"):
                chunks.append(chunk)
        assert mock_ask.called
        call_kwargs = mock_ask.call_args.kwargs
        assert call_kwargs.get("question") == "hello there"

    @pytest.mark.asyncio
    async def test_dispatches_to_swarm_for_code(self):
        from modes.auto_mode import auto_run
        with patch("modes.auto_mode.swarm_run") as mock_swarm:
            mock_swarm.return_value = _async_gen()
            async for _ in auto_run("build a new app"):
                pass
        assert mock_swarm.called
        call_kwargs = mock_swarm.call_args.kwargs
        assert call_kwargs.get("task") == "build a new app"

    @pytest.mark.asyncio
    async def test_dispatches_to_plan(self):
        from modes.auto_mode import auto_run
        with patch("modes.auto_mode.plan") as mock_plan:
            mock_plan.return_value = _async_gen()
            async for _ in auto_run("plan a new architecture"):
                pass
        assert mock_plan.called

    @pytest.mark.asyncio
    async def test_dispatches_to_mesh(self):
        from modes.auto_mode import auto_run
        with patch("modes.auto_mode.aquaculture_mesh_run", new_callable=AsyncMock) as mock_mesh:
            async for _ in auto_run("check sensor readings"):
                pass
        assert mock_mesh.called

    @pytest.mark.asyncio
    async def test_yields_intent_event_first(self):
        from modes.auto_mode import auto_run
        with patch("modes.auto_mode.ask") as mock_ask:
            mock_ask.return_value = _async_gen()
            chunks = []
            async for chunk in auto_run("hello"):
                chunks.append(chunk)
        assert len(chunks) >= 1
        first = chunks[0]
        assert "intent" in first
