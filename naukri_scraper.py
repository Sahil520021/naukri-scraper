#!/usr/bin/env python3
"""
Naukri Resdex CV Scraper
Replaces the entire n8n workflow with sequential execution
Handles multiple concurrent users via FastAPI
"""

import re
import time
import json
import random
import requests
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from concurrent.futures import ThreadPoolExecutor
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScraperInput(BaseModel):
    curlCommand: str
    maxResults: int = 500


class NaukriScraper:
    def __init__(self, curl_command: str, max_results: int = 500):
        self.curl_command = curl_command
        self.max_results = max_results
        self.session = requests.Session()
        
        # Configuration
        self.delay_between_profiles = 3  # seconds between individual profile fetches
        self.delay_between_pages = 2     # seconds between page changes
        self.max_retries = 2
        
        # Extracted data
        self.url = None
        self.headers = {}
        self.body = {}
        self.sid = None
        self.sid_group_id = None
        
    def parse_curl(self) -> Dict:
        """Parse cURL command to extract URL, headers, and body"""
        logger.info("Parsing cURL command...")
        
        # Normalize newlines
        normalized = self.curl_command.replace('\\\n', ' ').replace('\\n', ' ').replace('\n', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Extract URL
        url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?[']([^']+)[']", normalized, re.IGNORECASE)
        if not url_match:
            raise ValueError("Failed to extract URL from cURL")
        self.url = url_match.group(1)
        
        # Extract cookies - handles both -b and -H 'cookie:' formats
        cookie_value = None
        
        # Try -b flag
        b_flag_match = re.search(r"-b\s+(['\"])(.+?)\1\s+(?:-[A-Z]|--)", normalized, re.IGNORECASE)
        if b_flag_match:
            cookie_value = b_flag_match.group(2)
            logger.info(f"Cookie extracted from -b flag")
        else:
            b_flag_end = re.search(r"-b\s+(['\"])(.+?)\1\s*$", normalized, re.IGNORECASE)
            if b_flag_end:
                cookie_value = b_flag_end.group(2)
        
        # Try -H 'cookie:' format if -b didn't work
        if not cookie_value:
            h_flag_match = re.search(r"-H\s+(['\"])cookie:\s*(.+?)\1", normalized, re.IGNORECASE)
            if h_flag_match:
                cookie_value = h_flag_match.group(2)
                logger.info(f"Cookie extracted from -H header")
        
        if cookie_value:
            cookie_value = cookie_value.replace('\\"', '"').replace("\\'", "'")
            self.headers['cookie'] = cookie_value
            logger.info(f"Cookie length: {len(cookie_value)}")
        else:
            raise ValueError("No cookie found in cURL command")
        
        # Extract other headers
        header_pattern = r"-H\s+(['\"])([^:]+):\s*([^'\"]+)\1"
        for match in re.finditer(header_pattern, normalized, re.IGNORECASE):
            key = match.group(2).strip().lower()
            value = match.group(3).strip()
            if key != 'cookie' or key not in self.headers:
                self.headers[key] = value
        
        # Extract body
        body_match = re.search(r"(?:--data-raw|--data|-d)\s+(['{])(.+?)\1", normalized, re.IGNORECASE | re.DOTALL)
        if body_match:
            try:
                body_str = body_match.group(2).replace('\\"', '"').replace("\\'", "'")
                if not body_str.strip().startswith('{'):
                    body_str = '{' + body_str + '}'
                self.body = json.loads(body_str)
            except json.JSONDecodeError:
                # Fallback: manual extraction
                req_id = re.search(r'requirementId["\']:\s*["\']?(\d+)', normalized)
                company_id = re.search(r'companyId["\']:\s*(\d+)', normalized)
                user_id = re.search(r'rdxUserId["\']:\s*["\']([^"\']+)', normalized)
                user_name = re.search(r'rdxUserName["\']:\s*["\']([^"\']+)', normalized)
                
                self.body = {
                    'requirementId': req_id.group(1) if req_id else None,
                    'requirementGroupId': req_id.group(1) if req_id else None,
                    'newCandidatesSearch': False,
                    'saveSession': True,
                    'miscellaneousInfo': {
                        'companyId': int(company_id.group(1)) if company_id else None,
                        'rdxUserId': user_id.group(1) if user_id else None,
                        'rdxUserName': user_name.group(1) if user_name else None
                    }
                }
        
        # Add default headers if missing
        self.headers.setdefault('accept', 'application/json')
        self.headers.setdefault('accept-language', 'en-US,en;q=0.9')
        self.headers.setdefault('appid', '112')
        self.headers.setdefault('content-type', 'application/json')
        self.headers.setdefault('origin', 'https://resdex.naukri.com')
        self.headers.setdefault('systemid', 'naukriIndia')
        
        logger.info(f"Parsed URL: {self.url}")
        logger.info(f"Requirement ID: {self.body.get('requirementId')}")
        
        return {
            'url': self.url,
            'headers': self.headers,
            'body': self.body
        }
    
    def initial_search(self) -> Dict:
        """Perform initial search to get first 50 profiles and session data"""
        logger.info("Performing initial search...")
        
        # Generate transaction ID
        tx_id = f"rlsrp{int(time.time() * 1000)}~~{self._random_string(6)}"
        headers = self.headers.copy()
        headers['x-transaction-id'] = tx_id
        
        try:
            response = self.session.post(
                self.url,
                headers=headers,
                json=self.body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract session data
            self.sid = data.get('sid')
            self.sid_group_id = data.get('searchParams', {}).get('sidGroupId')
            
            if not self.sid or not self.sid_group_id:
                raise ValueError(f"Failed to extract session data. SID: {self.sid}, sidGroupId: {self.sid_group_id}")
            
            logger.info(f"Initial search successful. SID: {self.sid}, Total resumes: {data.get('totalResumes', 0)}")
            
            return {
                'sid': self.sid,
                'sidGroupId': self.sid_group_id,
                'tuples': data.get('tuples', []),
                'totalResumes': data.get('totalResumes', 0)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Initial search failed: {e}")
            raise
    
    def get_page(self, page_no: int) -> List[Dict]:
        """Get a specific page using pageChange endpoint"""
        logger.info(f"Fetching page {page_no}...")
        
        is_lite = '/rdxLite/' in self.url
        base_url = self.url.replace('/search', '/pageChange')
        
        tx_id = f"rlsrp{int(time.time() * 1000)}~~{self._random_string(6)}"
        headers = self.headers.copy()
        headers['x-transaction-id'] = tx_id
        
        body = {
            'pageNo': page_no,
            'miscellaneousInfo': {
                'companyId': self.body['miscellaneousInfo']['companyId'],
                'rdxUserId': self.body['miscellaneousInfo']['rdxUserId'],
                'rdxUserName': self.body['miscellaneousInfo']['rdxUserName'],
                'sid': self.sid,
                'sidGroupId': self.sid_group_id
            }
        }
        
        try:
            response = self.session.post(
                base_url,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Page {page_no} fetched successfully. Profiles: {len(data.get('tuples', []))}")
            return data.get('tuples', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page_no}: {e}")
            return []
    
    def get_individual_profile(self, profile: Dict, index: int, total: int, retry_count: int = 0) -> Optional[Dict]:
        """Fetch individual profile details"""
        is_lite = '/rdxLite/' in self.url
        path_type = 'rdxlite' if is_lite else 'rdx'
        page_name = 'rdxLitePreview' if is_lite else 'rdxPreview'
        flow_name = 'rdxLiteSrp' if is_lite else 'rdxSrp'
        
        company_id = self.body['miscellaneousInfo']['companyId']
        rdx_user_id = self.body['miscellaneousInfo']['rdxUserId']
        
        url = f"https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-services/v0/companies/{company_id}/recruiters/{rdx_user_id}/{path_type}/jsprofile"
        
        tx_id = f"rlsrp{int(time.time() * 1000)}~~{self._random_string(6)}"
        headers = self.headers.copy()
        headers['x-transaction-id'] = tx_id
        
        body = {
            'uniqId': profile.get('dynamicEncryptedUniqueId'),
            'pageName': page_name,
            'uname': None,
            'sid': str(self.sid),
            'requirementId': str(self.body['requirementId']),
            'requirementGroupId': str(self.body['requirementId']),
            'jsKey': profile.get('dynamicEncryptedJsKey'),
            'miscellaneousInfo': {
                'companyId': company_id,
                'rdxUserId': rdx_user_id,
                'resendOtp': False,
                'flowName': flow_name
            }
        }
        
        try:
            response = self.session.post(
                url,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"✅ [{index + 1}/{total}] Fetched: {profile.get('jsUserName', 'Unknown')}")
            return data
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            
            # Check for quota/CAPTCHA errors
            if 'QUOTA' in error_msg or 'Captcha' in error_msg or '403' in error_msg:
                logger.error(f"🛑 QUOTA EXHAUSTED OR CAPTCHA at profile {index + 1}")
                raise Exception("QUOTA_EXHAUSTED")
            
            # Retry logic
            if retry_count < self.max_retries:
                logger.warning(f"🔄 Retrying profile {index + 1} (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(5)
                return self.get_individual_profile(profile, index, total, retry_count + 1)
            
            logger.error(f"❌ [{index + 1}/{total}] Failed: {error_msg}")
            return None
    
    def scrape(self) -> Dict:
        """Main scraping logic"""
        start_time = time.time()
        
        try:
            # Step 1: Parse cURL
            self.parse_curl()
            
            # Step 2: Initial search
            search_result = self.initial_search()
            all_profiles = search_result['tuples']
            total_available = search_result['totalResumes']
            
            logger.info(f"Total available resumes: {total_available}")
            
            # Step 3: Get additional pages if needed
            pages_needed = min((self.max_results // 50), 10)  # Max 10 pages (500 profiles)
            
            for page_num in range(2, pages_needed + 1):
                time.sleep(self.delay_between_pages)
                page_profiles = self.get_page(page_num)
                all_profiles.extend(page_profiles)
                
                if len(all_profiles) >= self.max_results:
                    break
            
            # Limit to max_results
            all_profiles = all_profiles[:self.max_results]
            logger.info(f"Total profiles to fetch details for: {len(all_profiles)}")
            
            # Step 4: Fetch individual profiles SEQUENTIALLY
            detailed_profiles = []
            failed_count = 0
            
            for i, profile in enumerate(all_profiles):
                try:
                    # Delay before each request (except first)
                    if i > 0:
                        time.sleep(self.delay_between_profiles)
                    
                    detail = self.get_individual_profile(profile, i, len(all_profiles))
                    
                    if detail:
                        detailed_profiles.append(detail)
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    if "QUOTA_EXHAUSTED" in str(e):
                        logger.error(f"Stopping at profile {i + 1} due to quota/CAPTCHA")
                        break
                    failed_count += 1
            
            elapsed_time = time.time() - start_time
            
            logger.info(f"✅ Scraping complete!")
            logger.info(f"   Total profiles fetched: {len(detailed_profiles)}")
            logger.info(f"   Failed: {failed_count}")
            logger.info(f"   Time taken: {elapsed_time:.2f} seconds")
            
            return {
                'success': True,
                'total_fetched': len(detailed_profiles),
                'total_failed': failed_count,
                'time_taken_seconds': elapsed_time,
                'profiles': detailed_profiles
            }
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'profiles': []
            }
    
    @staticmethod
    def _random_string(length: int) -> str:
        """Generate random string for transaction IDs"""
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choice(chars) for _ in range(length))


# FastAPI app for handling concurrent requests
app = FastAPI(title="Naukri Resdex Scraper API")

# Thread pool for handling multiple scraping jobs
executor = ThreadPoolExecutor(max_workers=10)


@app.post("/scrape")
async def scrape_endpoint(input_data: ScraperInput):
    """
    Scrape Naukri Resdex profiles
    
    - **curlCommand**: cURL command from Naukri search request
    - **maxResults**: Maximum number of profiles to fetch (default: 500)
    """
    try:
        logger.info(f"New scraping request for {input_data.maxResults} profiles")
        
        scraper = NaukriScraper(
            curl_command=input_data.curlCommand,
            max_results=input_data.maxResults
        )
        
        result = scraper.scrape()
        
        return result
        
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    # Run FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
