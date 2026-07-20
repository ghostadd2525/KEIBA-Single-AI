FROM python:3.12-slim
WORKDIR /repo/services/win5-ai
COPY app ./app
# Expect mocks at /repo/public/data/mocks (mount repo root at /repo)
ENV PYTHONPATH=/repo/services/win5-ai
ENV AI_HOST=0.0.0.0
ENV AI_PORT=8000
EXPOSE 8000
CMD ["python", "-m", "app.main"]
