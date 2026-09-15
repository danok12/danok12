# Образ чат-бота. Контекст сборки — корень каталога решения.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv
COPY bot/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bot/bot ./bot
RUN useradd --system --uid 10002 botuser
USER botuser
CMD ["python", "-m", "bot.main"]
