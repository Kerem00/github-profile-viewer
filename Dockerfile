FROM alpine
RUN apk add --no-cache python3 py3-pip git
RUN pip3 install requests python-dotenv git+https://github.com/Rapptz/discord.py
WORKDIR /app
COPY . .
CMD ["python3", "bot.py"]