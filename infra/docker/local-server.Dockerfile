FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

WORKDIR /app

COPY server/pyproject.toml ./
COPY server/inkdesk_skill_sdk ./inkdesk_skill_sdk
COPY server/inkdesk_server ./inkdesk_server

RUN HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" \
    pip install --no-cache-dir ./inkdesk_skill_sdk \
    && HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" \
    pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "inkdesk_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
