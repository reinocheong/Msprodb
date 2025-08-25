FROM python:3.9-slim

WORKDIR /app

ENV WKHTMLTOPDF_VERSION 0.12.6.1-2

# Install dependencies, download, extract, and clean up in a single layer
RUN apt-get update && \
    # Install all necessary tools, including 'file' for verification
    apt-get install -y --no-install-recommends \
    curl \
    binutils \
    xz-utils \
    file \
    fonts-noto-cjk \
    libjpeg62-turbo \
    && \
    # Download the debian package for bullseye
    curl -L -o wkhtmltox.deb \
    "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.bullseye_amd64.deb" && \
    # --- Verification Step ---
    echo "Verifying downloaded file type:" && \
    file wkhtmltox.deb && \
    # -------------------------
    # Extract the deb archive and its contents
    ar x wkhtmltox.deb && \
    tar -xvf data.tar.xz && \
    # Copy the executables to a directory in the system's PATH
    cp ./usr/local/bin/wkhtmltopdf /usr/local/bin/ && \
    cp ./usr/local/bin/wkhtmltoimage /usr/local/bin/ && \
    # Clean up all the temporary files
    rm wkhtmltox.deb debian-binary control.tar.gz data.tar.xz && \
    rm -rf ./usr && \
    # Clean apt cache to keep the image small
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