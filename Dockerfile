# this docker file is used to create a docker image for the web.
# It currently is being built on dockerhub at dmbymdt/folioflex and
# then pulled down into a web container.
# To run dockerfile and create own image `docker build --no-cache -t folioflex .` 
# from where the dockerfile is located.
FROM python:3.9-slim

# Install git and chromium (lighter version of Chrome for seleniumbase)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git chromium && \
    ln -s /usr/bin/chromium /usr/bin/google-chrome && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# COPY files for web dashboard
COPY app.py ./assets /code/

# Install requirements
RUN pip install --no-cache-dir "git+https://github.com/jkoestner/folioflex.git@main#egg=folioflex[budget]"

# Create new user
RUN adduser --disabled-password --gecos '' ffx && \
    chown -R ffx:ffx /code && \
    chown -R ffx:ffx /usr/local/lib/python*/site-packages/seleniumbase/drivers
USER ffx

# Using port 8001 for web
EXPOSE 8001