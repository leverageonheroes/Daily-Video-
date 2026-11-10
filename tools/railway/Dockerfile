# Railway cron worker for the daily carousel videos (python -m pipeline.run carousel).
# Build context = repo root. The worker clones the LATEST repo at run time (scripts, music, state),
# renders, uploads, then commits state/carousel.json back.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY tools/railway/run_carousel.sh /app/run_carousel.sh
RUN chmod +x /app/run_carousel.sh
CMD ["/app/run_carousel.sh"]
