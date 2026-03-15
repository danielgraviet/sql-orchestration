"""
sandbox_runner.py

Runs a single candidate solution inside a Daytona sandbox and returns
a benchmark result dict.

Each call to run_in_sandbox():
  1. Creates a fresh Daytona sandbox
  2. Uploads the solution file + benchmark.py into it
  3. Executes: python benchmark.py <solution_file>
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SNAPSHOT = "daytonaio/sandbox:0.6.0-slim-id"
SANDBOX_DIR = "/home/daytona"
BENCHMARK_TIMEOUT = 10  # seconds — hard limit per sandbox execution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_error_result(sandbox_id: str, error: str) -> dict:
    return {
        "sandbox_id": sandbox_id,
        "passed": False,
        "error": error,
        "execution_time_ms": None,
        "memory_mb": None,
        "score": 0,
        "lines_of_code": None,
    }


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

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
    sandbox_id = solution_path.stem   # e.g. "solution_007"
    sandbox = None

    try:
        # ------------------------------------------------------------------
        # 1. Create sandbox
        # ------------------------------------------------------------------
        sandbox = await daytona.create(
            CreateSandboxFromSnapshotParams(
                snapshot=SNAPSHOT,
                language="python",
                auto_stop_interval=2,    # auto-stop after 2 min of inactivity
                auto_delete_interval=5,  # auto-delete 5 min after stopped
            )
        )

        # ------------------------------------------------------------------
        # 2. Upload files
        #    benchmark.py is the test harness; solution is the candidate code.
        #    Both land in /home/daytona/.
        # ------------------------------------------------------------------
        benchmark_code = Path("benchmark.py").read_bytes()
        solution_code  = solution_path.read_bytes()

        await sandbox.fs.upload_file(benchmark_code, f"{SANDBOX_DIR}/benchmark.py")
        await sandbox.fs.upload_file(solution_code,  f"{SANDBOX_DIR}/{solution_path.name}")

        # ------------------------------------------------------------------
        # 3. Execute benchmark
        #    Hard timeout of BENCHMARK_TIMEOUT seconds.
        #    stdout is expected to be a single JSON object.
        # ------------------------------------------------------------------
        response = await sandbox.process.exec(
            f"python {SANDBOX_DIR}/benchmark.py {SANDBOX_DIR}/{solution_path.name}",
            timeout=BENCHMARK_TIMEOUT,
        )

        # ------------------------------------------------------------------
        # 4. Parse result
        # ------------------------------------------------------------------
        stdout = (response.result or "").strip()

        # Find the JSON line (benchmark.py prints exactly one JSON object)
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

        # Ensure sandbox_id matches our local label even if benchmark used its own
        result["sandbox_id"] = sandbox_id
        return result

    except DaytonaTimeoutError:
        return _make_error_result(sandbox_id, "FAILED_TIMEOUT")

    except Exception as e:
        return _make_error_result(sandbox_id, f"FAILED_SANDBOX: {e}")

    finally:
        # Always destroy the sandbox — even if an error occurred above.
        # auto_stop_interval + auto_delete_interval act as a safety net
        # in case this delete call itself fails.
        if sandbox:
            try:
                await sandbox.delete()
            except Exception:
                pass
