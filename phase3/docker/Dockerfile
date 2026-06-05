# phase3/docker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system deps for torch and lightgbm
RUN apt-get update && apt-get install -y \
    libgomp1 gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_phase3.txt .
RUN pip install --no-cache-dir -r requirements_phase3.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
