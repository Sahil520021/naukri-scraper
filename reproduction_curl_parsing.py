import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockScraper:
    def __init__(self, curl_command):
        self.curl_command = curl_command
        self.url = None

    def parse_curl(self):
        logger.info("Parsing cURL command...")
        
        # 1. Normalize
        normalized = self.curl_command.replace('\\\n', ' ').replace('\\n', ' ').replace('\n', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        
        print(f"DEBUG NORMALIZED: {normalized}")

        # 2. Extract URL
        # Attempt 1: Single quotes
        url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?[']([^']+)[']", normalized, re.IGNORECASE)
        
        if not url_match:
            print("Failed regex 1 (single quotes)")
            # Attempt 2: Flexible quotes
            url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?[\"']([^\"]+)[\"']", normalized, re.IGNORECASE)  
            
        if not url_match:
            print("Failed regex 2 (flexible quotes)")
            raise ValueError("Failed to extract URL from cURL")
            
        self.url = url_match.group(1)
        print(f"SUCCESS URL: {self.url}")

# Multiline cURL simulating the user's input
MULTILINE_CURL = """curl 'https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-listing-services/v0/rdxLite/search' \
  -H 'accept: application/json' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'appid: 112' \
  -H 'content-type: application/json' \
  --data-raw '{"requirementId":"130761"}'"""

print("--- TEST 1: Multiline with backslashes ---")
try:
    MockScraper(MULTILINE_CURL).parse_curl()
except Exception as e:
    print(f"ERROR: {e}")

print("\n--- TEST 2: Multiline WITHOUT backslashes (Apify textarea often strips them?) ---")
CLEAN_MULTILINE = """curl 'https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-listing-services/v0/rdxLite/search' 
  -H 'accept: application/json' 
  --data-raw '{"req":1}'"""
try:
    MockScraper(CLEAN_MULTILINE).parse_curl()
except Exception as e:
    print(f"ERROR: {e}")
