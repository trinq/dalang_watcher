FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libpcap-dev \
    gcc \
    iputils-ping \
    net-tools \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir psycopg2-binary==2.9.9
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ .

EXPOSE 5000

CMD ["python", "app.py"]