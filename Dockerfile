# this docker file is used to create a docker image for the web.
# It currently is being built on dockerhub at dmbymdt/folioflex and
# then pulled down into a web container.
# To run dockerfile and create own image `docker build --no-cache -t folioflex .` 
# from where the dockerfile is located.
FROM python:3.9-slim

# Install git, chromium, and x11 display(lighter version of Chrome for seleniumbase)
# x11 are only needed when debugging
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium \
    git \
    xvfb \
    x11vnc \
    xfonts-base \
    xauth \
    x11-apps && \
    ln -s /usr/bin/chromium /usr/bin/google-chrome && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /code

# Install requirements (without copying the whole directory)
RUN uv pip install --no-cache-dir --system "git+https://github.com/jkoestner/folioflex.git@main"

# Create new user
RUN adduser --disabled-password --gecos '' ffx && \
    chown -R ffx:ffx /code && \
    chown -R ffx:ffx /usr/local/lib/python*/site-packages/seleniumbase/drivers
USER ffx

# Using port 8001 for web
EXPOSE 8001