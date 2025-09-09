FROM python:3.11-slim

# Set container working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY ./src /app/src

# The command to run the application will be provided by docker-compose
# But we can expose the port here for clarity
EXPOSE 8001
