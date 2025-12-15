FROM python:3.11-slim

# 1. Install Node.js and system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install Node.js Dependencies
COPY package.json .
# Generate package-lock (optional but good practice, skipping for simplicity)
RUN npm install

# 4. Copy Application Code
COPY . .

# 5. Setup Startup Script
RUN chmod +x start.sh

# 6. Run
EXPOSE 8000
CMD ["./start.sh"]