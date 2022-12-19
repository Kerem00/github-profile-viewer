FROM alpine
RUN apk add --no-cache python3 py3-pip
RUN pip3 install --no-cache-dir requests redis python-dotenv discord.py
WORKDIR /app
COPY . .
CMD ["python3", "bot.py"]
