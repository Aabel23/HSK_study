# --- Stage 1: build the React frontend -------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend-web
COPY frontend-web/package.json frontend-web/package-lock.json* ./
RUN npm install
COPY frontend-web/ ./
RUN npm run build

# --- Stage 2: Python runtime -------------------------------------------------
FROM python:3.11-slim AS runtime
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY scripts/ scripts/
COPY frontend/ frontend/
COPY data/.gitkeep data/.gitkeep
COPY pyproject.toml ./
COPY --from=frontend-build /app/frontend-web/dist/ frontend-web/dist/

ENV CHINESE_STUDY_ENV=production \
    CHINESE_STUDY_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
