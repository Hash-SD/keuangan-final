FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lib ./lib
COPY public ./public
COPY server.py .

EXPOSE 8092

ENV SUPERSET_DASHBOARD_BIND_HOST=0.0.0.0 \
    SUPERSET_DASHBOARD_BIND_PORT=8092

HEALTHCHECK --interval=20s --timeout=10s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8092/api/health', timeout=5)"

CMD ["python", "server.py"]
