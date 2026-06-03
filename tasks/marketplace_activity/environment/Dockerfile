FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py /tmp/marketplace_activity_generate.py

ENV MARKETPLACE_ACTIVITY_OUTPUT_DIR=/app
RUN python /tmp/marketplace_activity_generate.py && rm /tmp/marketplace_activity_generate.py
