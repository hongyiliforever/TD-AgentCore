FROM python:3.11-slim as builder

WORKDIR /usr/app/gpt

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"

COPY pyproject.toml .
COPY src src

RUN pip install --upgrade pip && \
    pip install . '.[lint]' '.[test]' '.[package]' \
    --default-timeout=600 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/

FROM python:3.11-slim as production

WORKDIR /usr/app/gpt

VOLUME /usr/app/gpt/logs

COPY --from=builder /usr/app/venv /usr/app/venv
COPY --from=builder /usr/app/gpt/src /usr/app/gpt/src
COPY docker/startup.sh startup.sh

ENV PATH="/usr/app/venv/bin:$PATH"
ENV PYTHONPATH=${PYTHONPATH}:.

EXPOSE 8000

CMD ["sh", "startup.sh"]
