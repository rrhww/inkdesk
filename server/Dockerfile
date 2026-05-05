FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY inkvault_server ./inkvault_server

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "inkvault_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
