FROM python:3.9-slim

WORKDIR /app

# Use the bullseye package, which is a better fit for python:3.9's base OS (Debian 11)
ENV WKHTMLTOPDF_VERSION 0.12.6.1-2

# Install dependencies, download, extract, and clean up in a single layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    binutils \
    xz-utils \
    fonts-noto-cjk \
    && \
    # Download the debian package for bullseye
    curl -L -o wkhtmltox.deb \
    "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.bullseye_amd64.deb" && \
    # --- Verification Step ---
    echo "Verifying downloaded file type:" && \
    file wkhtmltox.deb && \
    # -------------------------
    # A .deb file is an 'ar' archive. Extract it.
    ar x wkhtmltox.deb && \
    # The archive contains data.tar.xz, which holds the program files. Extract it.
    tar -xvf data.tar.xz && \
    # Copy the main executables to a directory in the system's PATH
    cp ./usr/local/bin/wkhtmltopdf /usr/local/bin/ && \
    cp ./usr/local/bin/wkhtmltoimage /usr/local/bin/ && \
    # Clean up all the temporary files
    rm wkhtmltox.deb debian-binary control.tar.gz data.tar.xz && \
    rm -rf ./usr && \
    # Clean apt cache to keep the image small
    apt-get purge -y --auto-remove curl binutils xz-utils && \
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