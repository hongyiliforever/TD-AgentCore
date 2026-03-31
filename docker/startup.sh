#!/bin/bash

export PYTHONPATH=${PYTHONPATH}:.

if [ -z "${OTEL_EXPORTER_OTLP_ENDPOINT}" ]; then
    uvicorn src.main:app --host 0.0.0.0 --port 8000
else
    printenv | grep "^OTEL_"
    opentelemetry-instrument uvicorn src.main:app --host 0.0.0.0 --port 8000
fi
