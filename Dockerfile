FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    REMBG_MODEL=u2net_human_seg \
    DATA_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from rembg import new_session; new_session('u2net_human_seg')"

COPY . .
RUN python scripts/fetch_fonts.py

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
