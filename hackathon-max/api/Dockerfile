# Сборка мини-приложения и образа API одним Dockerfile.
# Контекст сборки — корень каталога решения (см. compose.yaml).

# --- 1. сборка мини-приложения ---
FROM node:22-alpine AS miniapp
WORKDIR /build
# сначала манифесты: слой с зависимостями переиспользуется между сборками
COPY miniapp/package.json miniapp/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY miniapp/index.html miniapp/vite.config.js ./
COPY miniapp/src ./src
RUN npm run build

# --- 2. образ API ---
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/srv/data \
    DB_PATH=/data/profil10.sqlite3
WORKDIR /srv
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
COPY data ./data
COPY --from=miniapp /build/dist ./app/static
RUN useradd --system --uid 10001 appuser && mkdir -p /data && chown -R appuser /data
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=3).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
