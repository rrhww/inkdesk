FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY inkdesk_server ./inkdesk_server

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "inkdesk_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
