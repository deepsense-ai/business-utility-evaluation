FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generate.py /tmp/machinery_malfunctions_generate.py

ENV MACHINERY_MALFUNCTIONS_OUTPUT_DIR=/app
RUN python /tmp/machinery_malfunctions_generate.py && rm /tmp/machinery_malfunctions_generate.py
