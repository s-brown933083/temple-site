# Dockerfile for Tencent CloudBase Cloud Run
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

# CloudBase Cloud Run provides PORT env (default 8080)
ENV PORT=8080
EXPOSE 8080

# Use shell form to expand $PORT
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]
