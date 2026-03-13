# Task 06 — Build the Web Dashboard

## Goal
Add a real-time web dashboard that visualizes sandbox execution as it happens — a live grid of sandbox tiles that animate from "running" to "pass/fail", with a leaderboard and final winner reveal.

## Stack
- **FastAPI** — serves the dashboard and hosts the WebSocket endpoint
- **uvicorn** — ASGI server
- **Vanilla JS + CSS** — single `index.html`, no build step, no framework
- **WebSockets** — orchestrator pushes events to the browser as results arrive

## File Structure Additions

```
.
├── server.py          ← FastAPI app + WebSocket endpoint
├── static/
│   └── index.html     ← Single-page dashboard (self-contained)
```

## How It Connects to the Orchestrator

`orchestrator.py` currently appends results to `results.jsonl`. Extend it to also **broadcast each result** to all connected WebSocket clients the moment it arrives.

```python
# orchestrator.py addition
async def broadcast(result: dict):
    for ws in connected_clients:
        await ws.send_json(result)
```

`server.py` manages the WebSocket connections and starts the orchestrator as a background task when the run begins.

## WebSocket Event Schema

All events are JSON with a `type` field:

```json
{ "type": "run_started", "total": 25 }
{ "type": "sandbox_update", "sandbox_id": "sandbox_007", "status": "running" }
{ "type": "sandbox_update", "sandbox_id": "sandbox_007", "status": "passed", "score": 97.3, "execution_time_ms": 1.41 }
{ "type": "sandbox_update", "sandbox_id": "sandbox_007", "status": "failed", "error": "FAILED_TIMEOUT" }
{ "type": "run_complete", "best": { "sandbox_id": "sandbox_014", "score": 97.3, "execution_time_ms": 1.41 } }
```

## Dashboard Layout

```
+-----------------------------------------------+
|  500-Brain Agent          Running: 12  Done: 8 |
+-----------------------------------------------+
|  [ 001 ✓ ] [ 002 ✗ ] [ 003 ... ] [ 004 ✓ ]   |
|  [ 005 ... ] [ 006 ✓ ] [ 007 ✗ ] [ 008 ... ]  |
|  ... (grid of 25 tiles)                        |
+-----------------------------------------------+
|  LEADERBOARD                                   |
|  1. sandbox_014  score: 97.3  time: 1.41ms     |
|  2. sandbox_008  score: 94.1  time: 1.89ms     |
|  3. sandbox_021  score: 91.0  time: 2.10ms     |
+-----------------------------------------------+
|  WINNER (revealed on run_complete)             |
|  sandbox_014 — 1.41ms — Score: 97.3            |
+-----------------------------------------------+
```

## Tile States & Colors

| State | Color | Icon |
|-------|-------|------|
| pending | gray | `...` |
| running | blue pulse animation | `⟳` |
| passed | green | `✓` |
| failed | red | `✗` |

## Animations
- Tiles pulse blue while running
- Flip to green/red with a short CSS transition on result
- Leaderboard rows slide in sorted order as new results arrive
- Winner section fades in with a highlight when `run_complete` fires

## Running the Dashboard

```bash
python server.py
# Open http://localhost:8000
# Click "Run" to start the agent
```

The "Run" button in the browser triggers a POST to `/start` which kicks off the orchestrator.

## Dependencies to Add
```
fastapi
uvicorn
```

## Files to Create
- `server.py`
- `static/index.html`
