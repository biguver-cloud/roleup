FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY date/ ./date/
COPY .chainlit/ ./.chainlit/
COPY chainlit.md .

EXPOSE 8080

CMD chainlit run app/main.py --host 0.0.0.0 --port ${PORT:-8080}
