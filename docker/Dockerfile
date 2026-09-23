FROM python:3.11-slim

WORKDIR /app

# Layer caching: install pinned deps before copying source trees.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY src ./src
COPY config ./config

# MLflow 3.x file-store gate is opt-in per process (Pitfall 2); the
# container process does not inherit repo shell env, so set it here.
ENV MLFLOW_ALLOW_FILE_STORE=true

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
