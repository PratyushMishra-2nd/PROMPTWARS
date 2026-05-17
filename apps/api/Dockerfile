FROM python:3.12-slim

# WeasyPrint runtime deps (GTK, Pango, Cairo) — needed for PDF export
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 app

WORKDIR /app

COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app app ./app
RUN pip install --no-cache-dir -e .

# data dir mounted from repo root at build time
COPY --chown=app:app ../../data /app/data

ENV PYTHONUNBUFFERED=1
ENV API_HOST=0.0.0.0
ENV API_PORT=8080
EXPOSE 8080

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
