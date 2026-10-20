FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ARG CACHEBUST=20261020_v5

COPY main.py ./
COPY modern/ ./modern/
COPY api/__init__.py ./api/__init__.py
COPY api/v1/ ./api/v1/
COPY core/ ./core/

RUN mkdir -p /app/data

EXPOSE 8020

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8020"]
