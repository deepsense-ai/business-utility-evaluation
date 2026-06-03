FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py /tmp/bottleneck_employees_generate.py

ENV BOTTLENECK_EMPLOYEES_OUTPUT_DIR=/app
RUN python /tmp/bottleneck_employees_generate.py && rm /tmp/bottleneck_employees_generate.py
