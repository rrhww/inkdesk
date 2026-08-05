FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

WORKDIR /app

# Harness worktree leases and startup cleanup use the Git CLI.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY server/pyproject.toml ./
COPY server/inkdesk_skill_sdk ./inkdesk_skill_sdk
COPY server/inkdesk_server ./inkdesk_server
COPY server/vault/skills ./skills

RUN --mount=type=cache,target=/root/.cache/pip \
    HTTP_PROXY="$HTTP_PROXY" HTTPS_PROXY="$HTTPS_PROXY" NO_PROXY="$NO_PROXY" \
    pip install --retries 5 --timeout 120 ./inkdesk_skill_sdk .

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD python -c "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2))['status'] == 'ok'"

CMD ["python", "-m", "uvicorn", "inkdesk_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
