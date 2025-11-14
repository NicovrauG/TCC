FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    mesa-utils \
    ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia o PROJETO INTEIRO — 1 nível acima do Dockerfile
COPY .. .

RUN pip install --upgrade pip   
RUN pip install --no-cache-dir -r back/requirements.txt

CMD ["uvicorn", "back.app.server:app", "--host", "0.0.0.0", "--port", "8000"]
