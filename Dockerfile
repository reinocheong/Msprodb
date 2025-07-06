FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y wkhtmltopdf && apt-get clean
COPY . .
RUN chmod +x ./start.sh
CMD ["./start.sh"]
