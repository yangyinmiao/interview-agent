FROM python:3.12-slim

WORKDIR /app

# Configure apt proxy for China network (ARG only, not exported to runtime)
ARG HTTP_PROXY
ARG HTTPS_PROXY

RUN export http_proxy=$HTTP_PROXY && export https_proxy=$HTTPS_PROXY && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
