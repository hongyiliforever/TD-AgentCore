#!/bin/bash
set -e

case "$1" in
    api)
        exec uvicorn src.main:app --host 0.0.0.0 --port 8000
        ;;
    orchestrator)
        exec python -m src.services.orchestrator_service
        ;;
    agent)
        exec python -m src.services.agent_service
        ;;
    *)
        exec "$@"
        ;;
esac
