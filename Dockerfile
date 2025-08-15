FROM python:3.9-slim

WORKDIR /app

ENV WKHTMLTOPDF_VERSION 0.12.6.1-2

# Step 1: Install build dependencies. This also cleans the apt cache for this layer.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    binutils \
    xz-utils \
    fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# Step 2: Download the wkhtmltopdf package.
RUN curl -L -o wkhtmltox.deb \
    "https://github.com/wkhtmltopdf/packaging/releases/download/${WKHTMLTOPDF_VERSION}/wkhtmltox_${WKHTMLTOPDF_VERSION}.buster_amd64.deb"

# Step 3: Extract the .deb archive and then the data archive within it.
RUN ar x wkhtmltox.deb && \
    tar -xvf data.tar.xz

# Step 4: Copy the executables to the system's PATH and make them executable.
RUN cp ./usr/local/bin/wkhtmltopdf /usr/local/bin/ && \
    cp ./usr/local/bin/wkhtmltoimage /usr/local/bin/ && \
    chmod +x /usr/local/bin/wkhtmltopdf && \
    chmod +x /usr/local/bin/wkhtmltoimage

# Step 5: Clean up all temporary files from the extraction.
RUN rm wkhtmltox.deb debian-binary control.tar.gz data.tar.xz && \
    rm -rf ./usr

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the start script executable
RUN chmod +x ./start.sh

# Command to run the application
CMD ["./start.sh"]
