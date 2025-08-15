FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Define the version of wkhtmltopdf to install
ENV WKHTMLTOPDF_VERSION 0.12.6.1-2

# Install system dependencies and wkhtmltopdf from pre-compiled binary
RUN apt-get update && \
    # Install necessary tools: xz-utils for decompression, fonts for PDF content
    apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    fonts-noto-cjk \
    && \
    # Download the generic amd64 binary for buster, which is highly compatible
    curl -L -o wkhtmltox.deb \
    "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.buster_amd64.deb" && \
    # The .deb file is just an archive. We can extract the contents directly.
    # This avoids dpkg and its dependency issues.
    dpkg-deb -xv wkhtmltox.deb / && \
    # Clean up downloaded file
    rm wkhtmltox.deb && \
    # Clean apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the start script executable
RUN chmod +x ./start.sh

# Command to run the application
CMD ["./start.sh"]
