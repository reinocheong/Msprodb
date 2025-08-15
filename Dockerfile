FROM python:3.9-slim

WORKDIR /app

# Define the version of wkhtmltopdf to install
ENV WKHTMLTOPDF_VERSION 0.12.6.1-2

# Install system dependencies and wkhtmltopdf from pre-compiled binary
RUN apt-get update && \
    # Install necessary tools:
    # - curl: to download the package
    # - binutils: provides the 'ar' command to unpack .deb archives
    # - xz-utils: to decompress the .tar.xz data file
    # - fonts-noto-cjk: for CJK font support in PDFs
    apt-get install -y --no-install-recommends \
    curl \
    binutils \
    xz-utils \
    fonts-noto-cjk \
    && \
    # Download the debian package
    curl -L -o wkhtmltox.deb \
    "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.buster_amd64.deb" && \
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