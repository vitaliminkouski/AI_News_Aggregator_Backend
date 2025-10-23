FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN mkdir -p /srv/models && \
    python scripts/download_models.py --local-dir /srv/models

ENV HF_HOME=/srv/models \
    TRANSFORMERS_CACHE=/srv/models \
    SENTENCEPIECE_CACHE=/srv/models

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
