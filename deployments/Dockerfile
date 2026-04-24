FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY sql /app/sql

RUN pip install --no-cache-dir -e .

CMD ["uvicorn", "copytrading_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

