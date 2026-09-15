# Стенд-эмулятор Bot API MAX. Только для локальной проверки сценария
# (профиль demo в compose.yaml), в рабочем контуре не используется.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/mockmax/server.py ./server.py
RUN useradd --system --uid 10003 standuser
USER standuser
EXPOSE 8081
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8081"]
