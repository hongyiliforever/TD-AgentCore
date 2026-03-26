#!/bin/bash

if [ -z "${OTEL_EXPORTER_OTLP_ENDPOINT}" ]; then
  python src/main.py -H 0.0.0.0 -P 9003
else
  printenv | grep "^OTEL_"
  opentelemetry-instrument python src/main.py -H 0.0.0.0 -P 9003
fi

