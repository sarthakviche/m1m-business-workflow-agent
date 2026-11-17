FROM python:3.12-slim

# WeasyPrint needs Pango; the fonts cover the rupee sign and Indian scripts in names.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    fonts-liberation \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user. It only needs to write generated PDFs.
RUN useradd --create-home --uid 1000 munim \
    && mkdir -p /app/generated_docs \
    && chown -R munim:munim /app/generated_docs
USER munim

ENV PYTHONUNBUFFERED=1
# Hosts such as Render set PORT. Migrations run first, and a failure stops the deploy.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log --proxy-headers --forwarded-allow-ips='*'"]
