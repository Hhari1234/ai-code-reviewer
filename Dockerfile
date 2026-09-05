FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY pyproject.toml ./pyproject.toml
COPY reviewer ./reviewer
COPY api ./api
COPY docs ./docs

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
