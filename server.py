"""
server.py

FastAPI backend for the SQL agent competition demo.
Streams competition events over SSE and returns final results.
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from reporter import Event, EventType, Reporter


app = FastAPI(title="SQL Agent Competition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_runs: dict[str, dict[str, Any]] = {}


class SSEReporter(Reporter):
    def __init__(self, queue: asyncio.Queue):
        super().__init__()
        self._queue = queue

    def on_event(self, event: Event) -> None:
        super().on_event(event)
        payload = {
            "type": event.type.value,
            "sandbox_id": event.sandbox_id,
            "role": event.role,
            "result": event.result,
            "total": event.total,
            "completed": event.completed,
            "timestamp": event.timestamp,
        }
        self._queue.put_nowait(json.dumps(payload))


class RunRequest(BaseModel):
    task: str
    force: bool = False
    dry_run: bool = False


MOCK_RESULTS_PATH = Path(__file__).parent / "tests" / "fixtures" / "mock_results.json"

MOCK_WINNER_SQL = """SELECT
    c.customer_name,
    SUM(o.total_amount) AS total_spent,
    COUNT(o.id) AS order_count
FROM customers c
JOIN orders o ON o.customer_id = c.id
WHERE o.created_at >= date('now', '-90 days')
GROUP BY c.id, c.customer_name
ORDER BY total_spent DESC
LIMIT 10;"""

MOCK_RATIONALE = (
    "This query uses an indexed join on customer_id and filters on a date range "
    "that leverages the created_at index. The GROUP BY on the primary key avoids "
    "a full table scan and the LIMIT keeps the result set small."
)


async def _replay_dry_run(reporter: SSEReporter, task: str) -> dict:
    mock_results: list[dict] = json.loads(MOCK_RESULTS_PATH.read_text())
    total = len(mock_results)

    reporter.on_event(Event(type=EventType.GENERATION_START))
    await asyncio.sleep(0.6)
    reporter.on_event(Event(type=EventType.GENERATION_DONE, total=total))
    await asyncio.sleep(0.3)

    for r in mock_results:
        reporter.on_event(Event(
            type=EventType.SANDBOX_START,
            sandbox_id=r["sandbox_id"],
            role=r["role"],
        ))

    completed = 0
    delays = [1.1, 0.9, 1.3, 1.5, 0.7]
    for i, r in enumerate(mock_results):
        await asyncio.sleep(delays[i % len(delays)])
        completed += 1
        event_type = EventType.SANDBOX_DONE if r["passed"] else EventType.SANDBOX_FAILED
        reporter.on_event(Event(
            type=event_type,
            sandbox_id=r["sandbox_id"],
            role=r["role"],
            result=r,
            completed=completed,
            total=total,
        ))

    sorted_results = sorted(mock_results, key=lambda x: x.get("score", 0), reverse=True)
    passing = [r for r in sorted_results if r.get("passed") and r.get("score", 0) > 0]
    winner = passing[0] if passing else sorted_results[0]
    latencies = [r["latency_ms"] for r in passing if r.get("latency_ms") is not None]

    def _median(vals: list[float]) -> float | None:
        if not vals:
            return None
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 != 0 else (s[mid - 1] + s[mid]) / 2

    competition_result = {
        "task": task,
        "winner": {**winner, "rationale": MOCK_RATIONALE},
        "winner_sql": MOCK_WINNER_SQL,
        "all_results": sorted_results,
        "sandboxes_run": len(mock_results),
        "success_count": len(passing),
        "failed_count": len(mock_results) - len(passing),
        "p50_latency_ms": _median(latencies),
        "best_score": winner.get("score", 0),
    }

    reporter.on_event(Event(type=EventType.COMPETITION_DONE, result=competition_result))
    return competition_result


async def _run_real(reporter: SSEReporter, task: str, force: bool) -> dict:
    from daytona_sdk import AsyncDaytona
    from data.schema_loader import get_schema_string
    from orchestrator import run_competition

    schema = get_schema_string()
    async with AsyncDaytona() as daytona:
        return await run_competition(task, schema, daytona, force=force, reporter=reporter)


async def _execute_run(run_id: str, task: str, force: bool, dry_run: bool) -> None:
    run = _runs[run_id]
    queue: asyncio.Queue = run["queue"]
    reporter = SSEReporter(queue)

    try:
        if dry_run:
            result = await _replay_dry_run(reporter, task)
        else:
            result = await _run_real(reporter, task, force)
        run["result"] = result
    except Exception as exc:
        run["error"] = str(exc)
        error_payload = json.dumps({"type": "error", "message": str(exc)})
        queue.put_nowait(error_payload)
    finally:
        run["done"] = True
        queue.put_nowait(None)


@app.post("/api/run")
async def start_run(req: RunRequest):
    run_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _runs[run_id] = {"queue": queue, "result": None, "error": None, "done": False}
    asyncio.create_task(_execute_run(run_id, req.task, req.force, req.dry_run))
    return {"run_id": run_id}


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _runs[run_id]
    queue: asyncio.Queue = run["queue"]

    async def event_generator():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield {"data": item}
            try:
                parsed = json.loads(item)
                if parsed.get("type") == EventType.COMPETITION_DONE.value:
                    break
            except Exception:
                pass

    return EventSourceResponse(event_generator())


@app.get("/api/run/{run_id}/result")
async def get_result(run_id: str):
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail="Run not found")
    run = _runs[run_id]
    if not run["done"]:
        raise HTTPException(status_code=202, detail="Run not complete")
    if run["error"]:
        raise HTTPException(status_code=500, detail=run["error"])
    return run["result"]


_frontend_dist = Path(__file__).parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
