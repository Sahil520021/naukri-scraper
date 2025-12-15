#!/bin/bash

# 1. Start Python API in the background
echo "🚀 Starting Python Scraper Backend..."
uvicorn naukri_scraper_async:app --host 0.0.0.0 --port 8000 &

# 2. Wait for it to be ready
echo "⏳ Waiting for Python server to init..."
sleep 5

# 3. Start Apify Actor (Main Process)
echo "🚀 Starting Apify Actor..."
node apify_actor_main.js
