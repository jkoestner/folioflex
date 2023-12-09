# this docker file is used to create a docker image for the web.
# It currently is being built on dockerhub at dmbymdt/folioflex and
# then pulled down into a web container.
# To run dockerfile and create own image `docker build --no-cache -t folioflex .` 
# from where the dockerfile is located.
FROM python:3.8-slim

# Install git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN apt-get update && \
    apt-get install -y wget gnupg2 && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /code

# Copy the current directory contents into the container
COPY . .

# Install requirements
RUN pip install .
RUN pip install .[gpt]
RUN pip install .[web]
RUN pip install .[worker]

# Create new user
RUN adduser --disabled-password --gecos '' ffx
RUN chown -R ffx:ffx /code
USER ffx

# Using port 8001 for web
EXPOSE 8001