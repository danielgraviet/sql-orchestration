"""
agent.py

Generates one SQL candidate per role using Claude, all fired in parallel.
Each successful response is saved as a .py file in solutions/ that exposes
a get_sql() function consumed by benchmark.py.
"""

import asyncio
import json
import re
import shutil
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from roles import ROLES

load_dotenv()

MODEL = "claude-sonnet-4-6"
SOLUTIONS_DIR = Path("solutions")

_SOLUTION_TEMPLATE = """\
# role: {role_name}
# rationale: {rationale}

SQL = \"\"\"
{sql}
\"\"\"

INDEX_DDL = {index_ddl}

def get_sql() -> str:
    return SQL.strip()
"""


def _build_user_message(task: str, schema: str) -> str:
    return f"Task: {task}\n\nSchema:\n{schema}"


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Claude ignores the instruction."""
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _write_solution(role_name: str, rationale: str, sql: str, index_ddl: str | None, index: int) -> Path:
    """Write a solution .py file and return its path."""
    safe_sql = sql.replace('"""', '""\\"')
    safe_index = index_ddl.replace('"""', '""\\"') if index_ddl else None
    index_line = f'"""{safe_index}"""' if safe_index else "None"

    content = _SOLUTION_TEMPLATE.format(
        role_name=role_name,
        rationale=rationale,
        sql=safe_sql,
        index_ddl=index_line,
    )

    path = SOLUTIONS_DIR / f"solution_{index:03d}.py"
    path.write_text(content)
    return path


async def _generate_one(
    client: anthropic.AsyncAnthropic,
    role: dict,
    task: str,
    schema: str,
    index: int,
) -> Path | None:
    try:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=0.2,
            system=role["system_prompt"],
            messages=[{"role": "user", "content": _build_user_message(task, schema)}],
        )
        raw = _strip_fences(message.content[0].text)
        data = json.loads(raw)

        if "sql" not in data or "role" not in data:
            return None

        return _write_solution(
            role_name=data["role"],
            rationale=data.get("rationale", ""),
            sql=data["sql"],
            index_ddl=data.get("index_ddl"),
            index=index,
        )

    except (json.JSONDecodeError, KeyError, IndexError):
        return None
    except Exception:
        return None


async def generate_solutions(task: str, schema: str, force: bool = False) -> list[Path]:
    """
    Generate one SQL candidate per role in parallel.
    If solutions already exist and force=False, returns cached files without calling the API.
    Pass force=True to clear and regenerate.
    """
    if SOLUTIONS_DIR.exists():
        cached = sorted(SOLUTIONS_DIR.glob("solution_*.py"))
        if cached and not force:
            return cached
        shutil.rmtree(SOLUTIONS_DIR)
    SOLUTIONS_DIR.mkdir()

    client = anthropic.AsyncAnthropic()

    results: list[Path | None | BaseException] = await asyncio.gather(
        *[_generate_one(client, role, task, schema, i + 1) for i, role in enumerate(ROLES)],
        return_exceptions=True,
    )

    saved = [r for r in results if isinstance(r, Path)]
    return saved
