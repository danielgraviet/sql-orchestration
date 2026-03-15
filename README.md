# SQL Agent Competition

Five specialized Claude agents compete in real time to write the best SQL for your task. Each runs in an isolated Daytona sandbox, gets scored on correctness, latency, and safety, and the winner is surfaced with a full rationale.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Node.js 18+
- An Anthropic API key
- A Daytona account (optional — use **Dry Run** to demo without one)

## Setup

```bash
# 1. Install Python dependencies
uv sync

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Set environment variables
cp .env.example .env   # then fill in your keys
```

Required variables in `.env`:

```
ANTHROPIC_API_KEY=sk-...
DAYTONA_API_KEY=...       # not needed for dry run
```

## Running

```bash
make dev
```

This starts the FastAPI backend on `http://localhost:8000` and the Vite dev server on `http://localhost:5173`. Open the Vite URL in your browser.

## How it works

1. Enter a natural-language SQL task (e.g. *"Top 10 customers by spend in the last 90 days"*)
2. Click **Run** to execute for real, or **Dry Run** to replay a recorded result instantly
3. Five agents generate SQL simultaneously, each with a different perspective:

| Agent | Focus |
|---|---|
| Query Planner | Correctness and readability |
| Performance Hacker | Minimize latency and scan cost |
| Safety Cop | Detect injection or destructive statements |
| Regression Tester | Edge cases and result validation |
| Narrator | Human-readable explanation |

4. Each candidate runs in its own isolated sandbox — bad SQL fails safely
5. The orchestrator scores every result and picks the winner

## Project structure

```
├── server.py          # FastAPI backend, SSE stream
├── orchestrator.py    # Competition logic and scoring
├── agent.py           # Claude prompt + SQL generation per role
├── reporter.py        # Event system (terminal + SSE)
├── benchmark.py       # In-sandbox evaluator
├── sandbox_runner.py  # Daytona sandbox lifecycle
├── data/              # Schema and seed data
├── tests/             # Pytest suite + mock fixtures
└── frontend/          # React + Vite UI
```
