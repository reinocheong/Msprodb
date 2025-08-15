FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# Step 1: Update apt and install necessary tools including fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    fonts-noto-cjk \
    && apt-get clean

# Step 2: Download and install a specific, known-working version of wkhtmltopdf
# This version is for Debian 12 (Bookworm), which is compatible with the base image.
RUN curl -L -o wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb && \
    dpkg -i wkhtmltox.deb && \
    # Install any missing dependencies and then clean up
    apt-get install -f -y && \
    rm wkhtmltox.deb

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the start script executable
RUN chmod +x ./start.sh

# Command to run the application
CMD ["./start.sh"]