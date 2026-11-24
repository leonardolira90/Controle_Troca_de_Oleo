FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE=/data/troca_oleo.sqlite \
    PROXY_FIX=1 \
    SESSION_COOKIE_SECURE=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY wsgi.py .

RUN useradd --create-home appuser && mkdir -p /data && chown appuser /data /app
USER appuser

# O banco SQLite fica em /data: monte um volume persistente nesse caminho.
VOLUME ["/data"]
EXPOSE 8000
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - wsgi:app"]
