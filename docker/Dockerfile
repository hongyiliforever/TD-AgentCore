FROM coolbeevip/langchain-cpu:3.11-0.3.27 as builder
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
WORKDIR /usr/app/gpt
RUN python -m venv /usr/app/venv
ENV PATH="/usr/app/venv/bin:$PATH"
COPY pyproject.toml .
COPY src src
COPY startup.sh startup.sh
RUN pip install . '.[lint]' '.[test]' '.[package]' \
    --trusted-host nexus.oss.asiainfo.com --default-timeout=600 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    -i http://nexus.oss.asiainfo.com:8099/nexus/repository/pypi-group/simple/

# 如果不需要源代码保护，可以删除下面这行
# RUN python $(python -c "import site; print(site.getsitepackages()[0])")/an_copilot/framework/utils/compile.py build_ext

# 目前项目用不到 torch，所以先删除，可以减少发布包尺寸
RUN rm -rf /usr/app/venv/lib/python3.11/site-packages/torch

FROM python:3.11-slim as production
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
WORKDIR /usr/app/gpt
VOLUME /usr/app/gpt/logs
COPY --from=builder /usr/app/venv ../venv
COPY --from=builder /usr/app/gpt/src src
COPY --from=builder /usr/app/gpt/startup.sh startup.sh

EXPOSE 9003
ENV OTEL_SERVICE_NAME=an-copilot-gpt-demo
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_METRICS_EXPORTER=otlp
ENV CYTHON_COMPATIBLE=true
ENV PYTHONPATH=${PYTHONPATH}:.
ENV PATH="/usr/app/venv/bin:$PATH"
CMD [ "sh", "startup.sh" ]
