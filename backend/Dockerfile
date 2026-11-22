FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/entrypoint.sh .
RUN chmod +x entrypoint.sh
COPY --from=ui /ui/dist ./static

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
