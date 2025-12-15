#!/usr/bin/env python3
"""
Test script for Naukri Scraper
Run this to verify the scraper works with your cURL command
"""

import requests
import json
import sys

# Configuration
SCRAPER_URL = "http://localhost:8000"

# Your test cURL command (PASTE YOUR ACTUAL CURL HERE WHEN TESTING LOCALLY)
# DO NOT COMMIT YOUR REAL CURL WITH COOKIES TO GIT
TEST_CURL = """
curl 'https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-listing-services/v0/rdxLite/search' \\
  -H 'authority: resdex.naukri.com' \\
  -H 'accept: application/json' \\
  -H 'content-type: application/json' \\
  -H 'cookie: PASTE_YOUR_COOKIE_HERE' \\
  --data-raw '{"requirementId":"12345"}'
"""

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{SCRAPER_URL}/health", timeout=5)
        response.raise_for_status()
        print(f"✅ Health check passed: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_scrape(curl_command: str, max_results: int = 10):
    """Test scraping with small number of profiles"""
    print(f"\n🔍 Testing scrape endpoint (max {max_results} profiles)...")
    
    try:
        response = requests.post(
            f"{SCRAPER_URL}/scrape",
            json={
                "curlCommand": curl_command,
                "maxResults": max_results
            },
            timeout=300  # 5 minutes
        )
        
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            print(f"✅ Scraping successful!")
            
            # Handle nested data (Async Scraper) or flat (Old Scraper)
            data = result.get('data', result)
            
            # Support new "candidates" structure or old "data" structure
            total = data.get('totalCandidates', data.get('total_fetched'))
            failed = data.get('debug_info', {}).get('total_failed') if 'debug_info' in data else data.get('total_failed')
            time_taken = data.get('debug_info', {}).get('time_taken_seconds') if 'debug_info' in data else data.get('time_taken_seconds')
            
            print(f"   Profiles fetched: {total}")
            print(f"   Failed: {failed}")
            
            if time_taken is not None:
                print(f"   Time taken: {time_taken:.2f}s")
            
            # Show first profile as sample
            profiles = data.get('candidates', data.get('profiles', []))
            if profiles:
                first_profile = profiles[0]
                print(f"\n📋 Sample profile:")
                print(f"   Name: {first_profile.get('name')}")
                print(f"   Email: {first_profile.get('email')}")
                # Print a few mapped keys to verify formatting
                print(f"   Degree: {first_profile.get('ugDegree')}")
                print(f"   Skills: {str(first_profile.get('keySkills'))[:50]}...")
            
            return True
        else:
            print(f"❌ Scraping failed: {result.get('error')}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out. Scraping takes time, try increasing timeout.")
        return False
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 Naukri Scraper Test Suite")
    print("=" * 60)
    
    # Check if scraper is running
    if not test_health():
        print("\n⚠️  Make sure the scraper is running:")
        print("   python naukri_scraper.py")
        sys.exit(1)
    
    # Run scrape test
    success = test_scrape(TEST_CURL, max_results=5)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
        print("\n💡 Ready to use! Now you can:")
        print("   1. Increase maxResults to 500 for full scraping")
        print("   2. Deploy to cloud for production use")
        print("   3. Integrate with Apify actor")
    else:
        print("❌ Tests failed. Check the errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
