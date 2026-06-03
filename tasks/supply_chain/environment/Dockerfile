FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py /tmp/supply_chain_generate.py

ENV SUPPLY_CHAIN_OUTPUT_DIR=/app
RUN python /tmp/supply_chain_generate.py && rm /tmp/supply_chain_generate.py
