FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libopus0 \
    libopus-dev \
    libsodium-dev \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "discord.py[voice]" \
    "PyNaCl" \
    "yt-dlp" \
    --force-reinstall

WORKDIR /app
COPY . .
CMD ["python", "bot.py"]
