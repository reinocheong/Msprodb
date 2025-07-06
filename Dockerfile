FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - wkhtmltopdf: for PDF generation
# - fonts-noto-cjk: for Chinese font support in PDFs
RUN apt-get update && \
    apt-get install -y wkhtmltopdf fonts-noto-cjk && \
    apt-get clean

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make the start script executable
RUN chmod +x ./start.sh

# Command to run the application
CMD ["./start.sh"]

