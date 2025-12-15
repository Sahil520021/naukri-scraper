# Naukri Resdex CV Scraper - Deployment Guide

## 🎯 Overview

This Python-based scraper **replaces the entire n8n workflow** with:
- ✅ **Sequential execution** - No parallel batching issues
- ✅ **Concurrent users** - FastAPI handles multiple requests simultaneously
- ✅ **Easy deployment** - Docker container ready
- ✅ **Better control** - Configurable delays, retries, error handling

## 📦 What's Included

```
naukri_scraper/
├── naukri_scraper.py      # Main Python scraper with FastAPI
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── apify_actor_main.js    # Updated Apify actor
└── README.md              # This file
```

## 🚀 Deployment Options

### Option 1: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper
python naukri_scraper.py

# Server runs on http://localhost:8000
```

### Option 2: Docker (Recommended for Production)

```bash
# Build the Docker image
docker build -t naukri-scraper .

# Run the container
docker run -d -p 8000:8000 --name naukri-scraper naukri-scraper

# View logs
docker logs -f naukri-scraper
```

### Option 3: Deploy to Cloud

#### **Render.com** (FREE tier available)

1. Create account at render.com
2. Create new Web Service
3. Connect your Git repo
4. Set:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python naukri_scraper.py`
5. Deploy! You'll get a URL like: `https://naukri-scraper-xyz.onrender.com`

#### **Railway.app** (FREE $5/month credit)

1. Create account at railway.app
2. New Project → Deploy from GitHub
3. Select your repo
4. Railway auto-detects Python and deploys
5. Get URL from deployment

#### **AWS EC2 / DigitalOcean / Linode**

```bash
# SSH into server
ssh user@your-server

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone repo and deploy
git clone <your-repo>
cd <your-repo>
docker build -t naukri-scraper .
docker run -d -p 8000:8000 --restart always naukri-scraper
```

## 🔧 Configuration

Edit `naukri_scraper.py` to adjust:

```python
# In NaukriScraper.__init__():
self.delay_between_profiles = 3  # Seconds between individual profiles
self.delay_between_pages = 2     # Seconds between page changes
self.max_retries = 2             # Retry attempts for failed requests
```

**Speed vs CAPTCHA:**
- `delay_between_profiles = 2` → Faster, might trigger CAPTCHA after 50-100 profiles
- `delay_between_profiles = 3` → Safe (recommended)
- `delay_between_profiles = 5` → Very safe, slower

## 📡 API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-16T10:30:00"
}
```

### Scrape Endpoint

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "curlCommand": "curl ... [your full cURL command]",
    "maxResults": 500
  }'
```

Response:
```json
{
  "success": true,
  "total_fetched": 487,
  "total_failed": 13,
  "time_taken_seconds": 1524.3,
  "profiles": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "mobile": "9876543210",
      "textCv": "...",
      ...
    }
  ]
}
```

## 🔗 Integrate with Apify

### Update Apify Actor

1. Replace `main.js` with `apify_actor_main.js`
2. Set environment variable:
   ```
   PYTHON_SCRAPER_URL=https://your-deployed-scraper.com/scrape
   ```
3. Push to Apify

### Example Apify Input

```json
{
  "curlCommand": "curl 'https://resdex.naukri.com/...' -H 'accept: application/json' ...",
  "maxResults": 500
}
```

## ⚡ Performance

| Profiles | Delay | Time (approx) |
|----------|-------|---------------|
| 100      | 3s    | ~5 minutes    |
| 500      | 3s    | ~25 minutes   |
| 100      | 2s    | ~3.5 minutes  |
| 500      | 2s    | ~17 minutes   |

**Concurrent Users:**
- FastAPI + ThreadPoolExecutor handles up to **10 concurrent scraping jobs**
- Each job runs independently with its own session
- No interference between users

## 🔍 Monitoring

### View Logs

```bash
# Docker
docker logs -f naukri-scraper

# Direct Python
# Logs output to console automatically
```

### Log Format

```
2025-12-16 10:30:00 - __main__ - INFO - Parsing cURL command...
2025-12-16 10:30:01 - __main__ - INFO - Cookie extracted from -b flag
2025-12-16 10:30:02 - __main__ - INFO - Initial search successful. SID: 2544149
2025-12-16 10:30:05 - __main__ - INFO - ✅ [1/500] Fetched: Aditya Jhade
2025-12-16 10:30:08 - __main__ - INFO - ✅ [2/500] Fetched: Abhinandan Mangave
...
```

## 🛠️ Troubleshooting

### "Cannot connect to Python scraper"

- **Local**: Make sure server is running on `http://localhost:8000`
- **Docker**: Check container: `docker ps`
- **Cloud**: Verify deployment URL is correct

### "QUOTA_EXHAUSTED"

- Your Naukri account ran out of CV view credits
- Wait for quota reset (daily/monthly)
- Or use different account

### "403 Forbidden / Captcha required"

- Delays too short → Increase `delay_between_profiles`
- Cookies expired → Get fresh cURL command
- Try again after 10-15 minutes

### Scraping stops partway

- Check logs for errors
- Might be quota limit or session timeout
- Script will return partial results

## 🎨 Advanced: Multiple Workers

For even faster scraping across multiple accounts:

```python
# Deploy 5 instances of the scraper
# Each on different port with different Naukri account

# Instance 1: Port 8001 (Account A)
# Instance 2: Port 8002 (Account B)
# etc.

# Load balancer distributes requests across all instances
```

## 📊 Comparison: n8n vs Python

| Feature | n8n Workflow | Python Script |
|---------|-------------|---------------|
| Sequential execution | ❌ Batching issues | ✅ True sequential |
| Concurrent users | ⚠️ Limited | ✅ Up to 10 jobs |
| Deployment | Complex | ✅ Docker/Cloud |
| Speed control | ⚠️ Limited | ✅ Fully configurable |
| Error handling | ⚠️ Basic | ✅ Retry + logging |
| Monitoring | ⚠️ UI only | ✅ Logs + metrics |

## 🔐 Security Notes

- **Never** commit cURL commands with cookies to Git
- Use environment variables for sensitive config
- Rotate Naukri credentials regularly
- Deploy behind authentication if exposing publicly

## 📝 License

MIT License - Use freely for your recruitment automation!

---

**Need help?** Check logs first, then review the troubleshooting section above.

**Happy Scraping! 🚀**
