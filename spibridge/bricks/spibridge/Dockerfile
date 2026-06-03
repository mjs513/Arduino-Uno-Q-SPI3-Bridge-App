# syntax=docker/dockerfile:1
# Source: https://forum.arduino.cc/t/getting-a-neato-xv-11-lidar-working-on-the-q/1445568/18
FROM python:3.13-slim
WORKDIR /app
COPY app .
RUN apt-get update && apt-get install -y python3-dev python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt
# See: https://flask.palletsprojects.com/en/stable/cli/
CMD ["flask", "run", "--host", "0.0.0.0"]
