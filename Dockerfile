# this docker file is used to create a docker image for the worker.
# It currently is being built on dockerhub at dmbymdt/folioflex and
# then pulled down into a worker container that is used to process jobs.
# To run dockerfile and create own image `docker build --no-cache -t cq-worker .` 
# from where the dockerfile is located.
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
RUN pip install git+https://github.com/jkoestner/folioflex.git

RUN chown -R cq:cq /code

USER cq