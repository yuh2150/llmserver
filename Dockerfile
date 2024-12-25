FROM python:3.10-slim

# Install build dependencies for building C++ extensions
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container (make sure address_extractor.py is in the current directory)
COPY . /app

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your app will run on
EXPOSE 6006

# Command to run the application
CMD ["python", "/app/address_extractor.py"]
