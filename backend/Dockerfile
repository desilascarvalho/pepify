FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install deemon watchdog
COPY backend/ /app/
COPY frontend/ /app/frontend/
RUN mkdir -p /root/.config/deemon /root/.config/deemix /downloads /app/frontend/static/images
COPY backend/config/config.json /root/.config/deemon/config.json
COPY backend/deemix_config/config.json /root/.config/deemix/config.json
ENV DEEMON_DOWNLOAD_PATH=/downloads
EXPOSE 8813
CMD ["python", "app.py"]