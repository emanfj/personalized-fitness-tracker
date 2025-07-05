# Use the official slim Python 3.11 base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# install redis-cli for healthchecks
RUN apt-get update \
 && apt-get install -y redis-tools \
 && rm -rf /var/lib/apt/lists/*
 
# Copy only requirements first (so Docker can cache the install step)
COPY requirements.txt .

# Install all Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the image
COPY . .

# Default command (overridden by docker‐compose for publisher or writer)
CMD ["bash", "-c", "echo 'Specify a service command in docker-compose'"]
