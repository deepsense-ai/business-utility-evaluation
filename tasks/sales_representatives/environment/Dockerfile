FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py /tmp/sales_representatives_generate.py

ENV SALES_REP_OUTPUT_DIR=/app
RUN python /tmp/sales_representatives_generate.py && rm /tmp/sales_representatives_generate.py
