.PHONY: dev frontend backend

dev:
	@trap 'kill 0' SIGINT; \
	uv run uvicorn server:app --reload --port 8000 & \
	cd frontend && npm run dev & \
	wait
