# News_Bot
Follow this steps to run server on local machine:
1. Clone repository
2. Install Docker, Docker-compose
3. Get file .env from developers and copy to project root directory(to directory news_bot_backend). Make sure it contains `ML_SERVICE_URL` pointing to the deployed ML microservice (default `http://ml-service:8100`).
4. Build and run container with command "docker-compose up --build"
