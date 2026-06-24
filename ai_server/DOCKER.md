# Docker Deployment Guide

## Build the Docker Image

```bash
# From the ai_server directory
docker build -t athit0900/face-recognition-ai-server:latest .
```

## Run Locally with Docker

```bash
# Using docker run
docker run -d -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/face_recognition.db \
  -e SIMILARITY_THRESHOLD=0.60 \
  -e MODEL_NAME=buffalo_l \
  -v $(pwd)/data:/app/data \
  --name face-recognition-ai-server \
  athit0900/face-recognition-ai-server:latest

# Or using docker-compose
docker-compose up -d
```

## Push to Docker Hub

### 1. Login to Docker Hub

```bash
docker login
```

### 2. Tag the Image

```bash
docker tag face-recognition-ai-server:latest athit0900/face-recognition-ai-server:latest
```

### 3. Push the Image

```bash
docker push athit0900/face-recognition-ai-server:latest
```

## Pull and Run from Docker Hub

```bash
docker pull athit0900/face-recognition-ai-server:latest

docker run -d -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./data/face_recognition.db \
  -e SIMILARITY_THRESHOLD=0.60 \
  -e MODEL_NAME=buffalo_l \
  -v $(pwd)/data:/app/data \
  athit0900/face-recognition-ai-server:latest
```

## Environment Variables

| Variable               | Default                           | Description                           |
| ---------------------- | --------------------------------- | ------------------------------------- |
| `DATABASE_URL`         | `sqlite:///./face_recognition.db` | Database connection string            |
| `SIMILARITY_THRESHOLD` | `0.60`                            | Face recognition similarity threshold |
| `MODEL_NAME`           | `buffalo_l`                       | InsightFace model name                |
| `HOST`                 | `0.0.0.0`                         | Server host                           |
| `PORT`                 | `8000`                            | Server port                           |

## Volumes

- `./data:/app/data` - Persists database and face embeddings

## Health Check

The container includes a health check that verifies the API is responding on port 8000.

## API Endpoints

- `GET /` - Health check
- `POST /users` - Create user
- `GET /users` - List users
- `POST /users/{user_id}/images` - Upload user image
- `POST /train` - Train face recognition model
- `POST /verify` - Verify face identity
- `GET /logs` - View check-in logs
