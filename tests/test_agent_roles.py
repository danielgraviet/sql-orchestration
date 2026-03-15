"""
tests/test_agent_roles.py

Smoke tests for agent.py. Requires ANTHROPIC_API_KEY to be set.
Run with: pytest tests/test_agent_roles.py -v
"""

import importlib.util
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import generate_solutions
from data.schema_loader import get_schema_string
from roles import ROLES

TASK = "Top 10 riders by trips last month"


@pytest.fixture(scope="module")
async def solutions():
    paths = await generate_solutions(TASK, get_schema_string())
    return paths


@pytest.mark.asyncio
async def test_returns_one_file_per_role(solutions):
    assert len(solutions) == len(ROLES)


@pytest.mark.asyncio
async def test_all_files_exist(solutions):
    for path in solutions:
        assert path.exists(), f"{path} was not written to disk"


@pytest.mark.asyncio
async def test_each_solution_has_get_sql(solutions):
    for path in solutions:
        spec = importlib.util.spec_from_file_location("sol", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sql = mod.get_sql()
        assert isinstance(sql, str)
        assert len(sql) > 10


@pytest.mark.asyncio
async def test_each_solution_file_is_valid_python(solutions):
    for path in solutions:
        source = path.read_text()
        try:
            compile(source, str(path), "exec")
        except SyntaxError as e:
            pytest.fail(f"{path.name} has a syntax error: {e}")


@pytest.mark.asyncio
async def test_sql_contains_select(solutions):
    for path in solutions:
        spec = importlib.util.spec_from_file_location("sol", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert "SELECT" in mod.get_sql().upper(), f"{path.name} SQL does not contain SELECT"
