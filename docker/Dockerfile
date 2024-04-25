FROM debian:12

WORKDIR /var/www/threads

RUN apt-get update && \
 apt-get install -y \
 python3-dev \
 build-essential \
 libssl-dev \
 libffi-dev \
 python3-setuptools \
 python3-flask \
 python3-requests \
 gunicorn3

COPY . .
