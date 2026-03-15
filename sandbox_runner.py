"""
sandbox_runner.py

Runs a single candidate solution inside a Daytona sandbox and returns
a benchmark result dict.

Each call to run_in_sandbox():
  1. Creates a fresh Daytona sandbox
  2. Uploads benchmark.py, the solution, rides.db, and expected_top10.json
  3. Executes: python benchmark.py <solution_file> <db_path>
  4. Parses the JSON result from stdout
  5. Destroys the sandbox (always, in finally)

The AsyncDaytona client is created once by the orchestrator and passed in —
not created per-sandbox — so it can reuse its underlying HTTP session pool.
"""

import json
from pathlib import Path

from daytona_sdk import AsyncDaytona, CreateSandboxFromSnapshotParams
from daytona_sdk.common.errors import DaytonaTimeoutError
from dotenv import load_dotenv

load_dotenv()

SNAPSHOT = "daytonaio/sandbox:0.6.0-slim-id"
SANDBOX_DIR = "/home/daytona"
BENCHMARK_TIMEOUT = 10

DATA_DIR = Path("data")


def _make_error_result(sandbox_id: str, error: str) -> dict:
    return {
        "sandbox_id": sandbox_id,
        "role": None,
        "passed": False,
        "error": error,
        "latency_ms": None,
        "rows_returned": None,
        "explain_cost": None,
        "score": 0,
        "sql_length": None,
    }


async def run_in_sandbox(
    daytona: AsyncDaytona,
    solution_path: Path,
) -> dict:
    """
    Boot a sandbox, run the benchmark against one solution, return the result.

    Args:
        daytona:       Shared AsyncDaytona client (created once by orchestrator).
        solution_path: Local path to the candidate solution file.

    Returns:
        Result dict matching the schema defined in benchmark.py.
    """
    sandbox_id = solution_path.stem
    sandbox = None

    try:
        sandbox = await daytona.create(
            CreateSandboxFromSnapshotParams(
                snapshot=SNAPSHOT,
                language="python",
                auto_stop_interval=2,
                auto_delete_interval=5,
            )
        )

        # upload all files the benchmark needs
        await sandbox.fs.upload_file(Path("benchmark.py").read_bytes(),        f"{SANDBOX_DIR}/benchmark.py")
        await sandbox.fs.upload_file(solution_path.read_bytes(),               f"{SANDBOX_DIR}/{solution_path.name}")
        await sandbox.fs.upload_file((DATA_DIR / "rides.db").read_bytes(),     f"{SANDBOX_DIR}/rides.db")
        await sandbox.fs.upload_file((DATA_DIR / "expected_top10.json").read_bytes(), f"{SANDBOX_DIR}/expected_top10.json")

        response = await sandbox.process.exec(
            f"python {SANDBOX_DIR}/benchmark.py {SANDBOX_DIR}/{solution_path.name} {SANDBOX_DIR}/rides.db",
            timeout=BENCHMARK_TIMEOUT,
        )

        stdout = (response.result or "").strip()

        result = None
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    result = json.loads(line)
                    break
                except json.JSONDecodeError:
                    pass

        if result is None:
            return _make_error_result(sandbox_id, f"FAILED_PARSE: no JSON in stdout — got: {stdout[:200]}")

        result["sandbox_id"] = sandbox_id
        return result

    except DaytonaTimeoutError:
        return _make_error_result(sandbox_id, "FAILED_TIMEOUT")

    except Exception as e:
        return _make_error_result(sandbox_id, f"FAILED_SANDBOX: {e}")

    finally:
        if sandbox:
            try:
                await sandbox.delete()
            except Exception:
                pass
