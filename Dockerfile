FROM alpine
RUN apk add --no-cache python3 py3-pip py3-requests py3-redis py3-dotenv
RUN pip3 install --no-cache-dir --break-system-packages discord.py
WORKDIR /app
COPY . .
CMD ["python3", "bot.py"]
