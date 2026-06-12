FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY date/ ./date/
COPY .chainlit/ ./.chainlit/
COPY chainlit.md .

EXPOSE 8080

# app/ ディレクトリを作業ディレクトリにすることで
# api_routes.py / schemas.py 等の相互インポートが解決される
WORKDIR /app/app
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}
