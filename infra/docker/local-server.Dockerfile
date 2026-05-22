FROM postgres:17

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml ./
COPY inkvault_server ./inkvault_server

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "inkvault_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
