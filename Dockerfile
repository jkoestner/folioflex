# to run dockerfile `docker build --no-cache -t cq-worker .` from where the dockerfile is located
FROM python:3.8-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create new user
RUN adduser --disabled-password --gecos '' cq

# Set work directory
WORKDIR /code

# Install requirements
RUN pip install git+https://github.com/jkoestner/IEX.git

RUN chown -R cq:cq /code

USER cq