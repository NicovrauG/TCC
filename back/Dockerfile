FROM python:3.11-slim

WORKDIR /app

# Copia o PROJETO INTEIRO — 1 nível acima do Dockerfile
COPY .. .

RUN pip install --no-cache-dir -r back/requirements.txt

CMD ["uvicorn", "back.app.server:app", "--host", "0.0.0.0", "--port", "8000"]
