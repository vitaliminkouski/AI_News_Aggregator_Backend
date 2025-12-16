# News_Bot
## News Bot – Backend + ML Microservice

News Bot is a web service for collecting, processing, and serving news articles, built with FastAPI for the main API and a separate ML microservice for NLP-related tasks (classification, embeddings, etc.).

This README explains how to **get the project** and **run the entire stack with Docker** (backend, ML service, PostgreSQL, Redis, Celery worker & beat).

---

### System requirements

- **Git**
- **Docker** (Docker Engine)
- **Docker Compose**

You do **not** need a local Python environment to run the app with Docker.

---

## Follow these steps to run API

### 1. Clone the project

### 2. Configure environment variables

The project uses a root `.env` file for Docker Compose.

Create a file named `.env` in the project root (`News_Bot`) and ask developers for data for this file:


### 3. Run the entire project with Docker
From the project root (`News_Bot`):

### 4. Stop any previously running stack (optional but recommended)
docker compose down || docker-compose down

### 5. Build and start all services in the background
docker compose up --build -d

or, if you have the old binary:

docker-compose up --build -d

This will:

- Build the **backend** image from `news_bot_backend/Dockerfile`
- Build the **ML microservice** image from `ml_service/Dockerfile`
- Start:
  - `postgres` (PostgreSQL)
  - `redis`
  - `ml-service` (ML microservice)
  - `api` (FastAPI backend)
  - `worker` (Celery worker)
  - `beat` (Celery beat scheduler)

---

## Accessing the services

- **Backend API (FastAPI)**:  
  `http://localhost:8000`
- **API docs (Swagger UI)** (if enabled):  
  `http://localhost:8000/docs`
- **ML microservice**:  
  `http://localhost:8100`
- **PostgreSQL** (from host):  
  - Host: `localhost`
  - Port: `5433`
  - Database: `newsbot`
  - User: `newsbot_admin`
  - Password: value from `POSTGRES_PASSWORD` in `.env`
- **Redis** (from host):  
  - Host: `localhost`
  - Port: `6379`

---

### Managing the stack

- **Check running containers**:

 
  docker ps
  - **View logs** (all services):

 
  docker compose logs -f
  # or: docker-compose logs -f
  - **View logs for a specific service** (e.g., API):

 
  docker compose logs -f api
  - **Stop all services**:

 
  docker compose down
  # or: docker-compose down
  ---

### Development notes

- The root `docker-compose.yml` mounts the backend code:

  - Host path: `./news_bot_backend`
  - Container path: `/app`

  That means changes you make to the backend code on your machine are reflected inside the running containers (helpful for development, especially since `uvicorn` runs with `--reload`).

- There is also a separate `docker-compose.yml` inside `news_bot_backend/` intended for backend-only usage.  
  For running the **full project (backend + ML)**, always use the **root** `docker-compose.yml` as described above.
