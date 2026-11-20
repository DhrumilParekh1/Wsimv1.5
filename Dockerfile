FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WRESTLING_SIM_SAVE=/data/campaign.db \
    RINGSIDE_REAL_DATA_DB=/data/real_wrestlers.db \
    RINGSIDE_START_MODE=real

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir . && \
    useradd --create-home --shell /usr/sbin/nologin ringside && \
    mkdir -p /data && chown -R ringside:ringside /data /app

USER ringside
EXPOSE 8000
HEALTHCHECK --interval=40s --timeout=8s --start-period=25s --retries=3 \
    CMD python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/health',timeout=5).status==200"
CMD ["uvicorn","wrestling_sim.api:app","--host","0.0.0.0","--port","8000","--workers","1"]
