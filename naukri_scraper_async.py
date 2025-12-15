#!/usr/bin/env python3
"""
Naukri Resdex CV Scraper (Async)
Designed for high-performance concurrent scraping as an Apify Actor.
Supports multiple simultaneous users via FastAPI + AsyncIO.
"""

import re
import json
import random
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NaukriScraper")


class ScraperInput(BaseModel):
    curlCommand: str
    maxResults: int = 500
    concurrency: int = 5  # Number of parallel profile fetches per request


class AsyncNaukriScraper:
    def __init__(self, curl_command: str, max_results: int = 500, concurrency: int = 5):
        self.curl_command = curl_command
        self.max_results = max_results
        self.concurrency = concurrency
        
        # Configuration
        self.max_retries = 3
        # We'll use a semaphore to limit concurrency for *this specific request*
        self.sem = asyncio.Semaphore(concurrency)
        
        # Session state
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Extracted data
        self.url: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.body: Dict[str, Any] = {}
        self.sid: Optional[str] = None
        self.sid_group_id: Optional[str] = None
        
    @staticmethod
    def _random_string(length: int) -> str:
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        return ''.join(random.choice(chars) for _ in range(length))

    def _generate_transaction_id(self) -> str:
        return f"rlsrp{int(time.time() * 1000)}~~{self._random_string(6)}"

    def parse_curl(self) -> Dict:
        """
        Robust cURL parsing. Extracts URL, Headers, Body, and Cookies.
        """
        logger.info("Parsing cURL command...")
    
        # DEBUG LOGGING FOR APIFY
        logger.info(f"Raw cURL input length: {len(self.curl_command)}")
        logger.info(f"Raw cURL start (first 100 chars): {self.curl_command[:100]!r}")

        # 1. Normalize
        normalized = self.curl_command.replace('\\\n', ' ').replace('\\n', ' ').replace('\n', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        
        logger.info(f"Normalized cURL (first 100 chars): {normalized[:100]!r}")
        
        # 2. Extract URL
        url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?[']([^']+)[']", normalized, re.IGNORECASE)
        if not url_match:
            url_match = re.search(r"curl\s+(?:-X\s+\w+\s+)?[\"']([^\"']+)[\"']", normalized, re.IGNORECASE)  
        if not url_match:
            raise ValueError("Failed to extract URL from cURL")
        self.url = url_match.group(1)
        
        # 3. Cookies
        cookie_str = None
        b_flag_matches = list(re.finditer(r"-b\s+(['\"])(.+?)\1", normalized))
        if b_flag_matches:
            cookie_str = b_flag_matches[0].group(2)
        
        if not cookie_str:
            h_cookie_matches = list(re.finditer(r"-H\s+(['\"])cookie:\s*(.+?)\1", normalized, re.IGNORECASE))
            if h_cookie_matches:
                cookie_str = h_cookie_matches[0].group(2)

        self.cookies_dict = {}
        if cookie_str:
            cookie_str = cookie_str.replace('\\"', '"').replace("\\'", "'")
            # Set init header to raw string to ensure safely working initial request
            self.headers['cookie'] = cookie_str
            
            # Parse into dict for future updates
            try:
                from http.cookies import SimpleCookie
                cookie = SimpleCookie()
                cookie.load(cookie_str)
                for key, morsel in cookie.items():
                    self.cookies_dict[key] = morsel.value
                
                logger.info(f"Parsed {len(self.cookies_dict)} cookies from cURL")
            except Exception as e:
                logger.error(f"Cookie parsing failed: {e}")
                # cookie_str is already set in headers, so we are good
                logger.error(f"Cookie parsing failed: {e}")
                # cookie_str is already set in headers, so we are good

        # 4. Headers
        header_iter = re.finditer(r"-H\s+(['\"])([^:]+):\s*([^'\"]+)\1", normalized, re.IGNORECASE)
        for match in header_iter:
            key = match.group(2).strip().lower()
            val = match.group(3).strip()
            if key in ['cookie', 'content-length', 'accept-encoding']: continue
            self.headers[key] = val

        # 5. Body
        body_match = re.search(r"(?:--data-raw|--data|-d)\s+(['{])(.+?)\1", normalized, re.IGNORECASE)
        if body_match:
            try:
                raw_body = body_match.group(2).replace('\\"', '"').replace("\\'", "'")
                if not raw_body.strip().startswith('{'):
                    raw_body = '{' + raw_body + '}'
                self.body = json.loads(raw_body)
            except:
                self._manual_body_extraction(normalized)
        else:
             self._manual_body_extraction(normalized)
             
        # 6. Defaults
        defaults = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'appid': '112',
            'content-type': 'application/json',
            'origin': 'https://resdex.naukri.com',
            'systemid': 'naukriIndia',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }
        for k, v in defaults.items():
            self.headers.setdefault(k, v)
            
        return {'url': self.url, 'headers': self.headers, 'body': self.body}

    def _update_cookie_header(self):
        """Re-generate cookie header from cookies_dict"""
        if self.cookies_dict:
            self.headers['cookie'] = '; '.join([f"{k}={v}" for k, v in self.cookies_dict.items()])

    def _manual_body_extraction(self, text: str):
        # ... (keep existing) ...
        req_id = re.search(r'requirementId["\']:\s*["\']?(\d+)', text)
        company_id = re.search(r'companyId["\']:\s*(\d+)', text)
        user_id = re.search(r'rdxUserId["\']:\s*["\']([^"\']+)', text)
        user_name = re.search(r'rdxUserName["\']:\s*["\']([^"\']+)', text)
        
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

    async def initial_search(self) -> Dict:
        """Perform initial search request to establish session and get first page"""
        logger.info("Performing initial search...")
        
        headers = self.headers.copy()
        headers['x-transaction-id'] = self._generate_transaction_id()
        
        # 30s timeout to prevent hanging
        async with self.session.post(self.url, headers=headers, json=self.body, timeout=30) as response:
            if response.status != 200:
                text = await response.text()
                raise HTTPException(status_code=response.status, detail=f"Search failed: {text}")
                
            data = await response.json()
            
            # Check for cookie updates - DISABLED 
            # (Matches n8n behavior: uses original cURL cookie for all requests)
            # if response.cookies:
            #     for key, morsel in response.cookies.items():
            #         self.cookies_dict[key] = morsel.value
            #     self._update_cookie_header()
            #     logger.info(f"Updated cookies from response. Count: {len(self.cookies_dict)}")

            # Extract session data
            self.sid = data.get('sid')
            self.sid_group_id = data.get('searchParams', {}).get('sidGroupId')
            
            if not self.sid:
                # Some API versions might return sid differently
                raise ValueError("Could not find 'sid' in search response")
                
            return {
                'tuples': data.get('tuples', []),
                'totalResumes': data.get('totalResumes', 0)
            }

    async def get_page(self, page_no: int) -> List[Dict]:
        """Fetch a specific page of results"""
        if not self.url or not self.sid:
            return []
            
        # Construct Page Change URL
        # replace /search with /pageChange
        base_url = self.url.replace('/search', '/pageChange')
        
        headers = self.headers.copy()
        headers['x-transaction-id'] = self._generate_transaction_id()
        
        payload = {
            'pageNo': page_no,
            'miscellaneousInfo': {
                'companyId': self.body['miscellaneousInfo']['companyId'],
                'rdxUserId': self.body['miscellaneousInfo']['rdxUserId'],
                'rdxUserName': self.body['miscellaneousInfo'].get('rdxUserName'),
                'sid': self.sid,
                'sidGroupId': self.sid_group_id
            }
        }
        
        try:
            async with self.session.post(base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('tuples', [])
                else:
                    logger.error(f"Failed to fetch page {page_no}: Status {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching page {page_no}: {e}")
            return []

    async def get_individual_profile(self, profile: Dict) -> Optional[Dict]:
        async with self.sem:
            is_lite = '/rdxLite/' in (self.url or '')
            path_type = 'rdxlite' if is_lite else 'rdx'
            
            company_id = self.body['miscellaneousInfo']['companyId']
            rdx_user_id = self.body['miscellaneousInfo']['rdxUserId']
            
            detail_url = f"https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-services/v0/companies/{company_id}/recruiters/{rdx_user_id}/{path_type}/jsprofile"
            
            page_name = 'rdxLitePreview' if is_lite else 'rdxPreview'
            flow_name = 'rdxLiteSrp' if is_lite else 'rdxSrp'
            
            payload = {
                'uniqId': profile.get('dynamicEncryptedUniqueId'),
                'pageName': page_name,
                'uname': None,
                'sid': str(self.sid),
                'requirementId': str(self.body.get('requirementId')),
                'requirementGroupId': str(self.body.get('requirementId')),
                'jsKey': profile.get('dynamicEncryptedJsKey'),
                'miscellaneousInfo': {
                    'companyId': company_id,
                    'rdxUserId': rdx_user_id,
                    'resendOtp': False,
                    'flowName': flow_name
                }
            }
            
            headers = self.headers.copy()
            headers['x-transaction-id'] = self._generate_transaction_id()
             
            for attempt in range(self.max_retries):
                try:
                    async with self.session.post(detail_url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status in [403, 429]:
                            logger.warning(f"Rate limited ({response.status}). Pausing...")
                            await asyncio.sleep(2 * (attempt + 1))
                        else:
                            # Log warning but don't spam body unless critical
                            logger.warning(f"Profile fetch failed: Status {response.status}")
                            if response.status == 401:
                                break
                except Exception as e:
                    logger.error(f"Profile fetch error: {e}")
                
                await asyncio.sleep(1)
            return None

    async def run(self):
        """Execute the full scraping workflow"""
        
        # 1. Parse Input to get cookies first
        try:
            self.parse_curl()
        except Exception as e:
            return {'success': False, 'error': f"CURL Parsing Error: {str(e)}"}

        # Initialize Session
        # We don't set default headers here because we want full control per request
        timeout = aiohttp.ClientTimeout(total=600) # 10 minutes total
        async with aiohttp.ClientSession(timeout=timeout) as session:
            self.session = session
            
            start_time = time.time()
            
            # 2. Initial Search
            try:
                search_res = await self.initial_search()
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Initial Search Traceback: {traceback.format_exc()}")
                return {'success': False, 'error': f"Initial Search Error: {repr(e)}"}
                
            all_tuples = search_res['tuples']

            total_available = search_res['totalResumes']
            logger.info(f"Initial search found {total_available} resumes. Loaded {len(all_tuples)}.")
            
            # 3. Fetch Additional Pages (Concurrent)
            # Calculate how many pages we need
            # Standard page size is 50
            needed = self.max_results - len(all_tuples)
            if needed > 0 and total_available > len(all_tuples):
                pages_to_fetch = []
                # Page 1 is already fetched. Start from 2.
                # Max pages limit? Let's say max 20 pages (1000 profiles) to be safe for now
                # User config maxResults dictates this.
                current_count = len(all_tuples)
                page_idx = 2
                
                while current_count < self.max_results and page_idx <= 20: 
                    pages_to_fetch.append(page_idx)
                    current_count += 50
                    page_idx += 1
                
                logger.info(f"Fetching {len(pages_to_fetch)} additional pages concurrently...")
                
                # Fetch pages concurrently
                # Ideally utilize a separate semaphore for pages if strict about traffic,
                # but pages are few compared to profiles.
                page_tasks = [self.get_page(p) for p in pages_to_fetch]
                page_results = await asyncio.gather(*page_tasks)
                
                for p_res in page_results:
                    all_tuples.extend(p_res)
            
            # Trim to max results
            all_tuples = all_tuples[:self.max_results]
            logger.info(f"Total profiles to fetch: {len(all_tuples)}")
            
            # 4. Fetch Individual Profiles (Concurrent)
            # The self.sem semaphore ensures we don't blast the API
            tasks = [self.get_individual_profile(t) for t in all_tuples]
            
            # Use asyncio.as_completed or gather. Gather is fine as we want all of them.
            # We can also add progress logging here if desired using a wrapper.
            
            results = await asyncio.gather(*tasks)
            
            # Filter successful and Format
            formatted_candidates = []
            for r in results:
                if r:
                    formatted_candidates.append(self._format_profile(r))
            
            failed = len(results) - len(formatted_candidates)
            duration = time.time() - start_time
            
            logger.info(f"Scraping completed. Fetched: {len(formatted_candidates)}, Failed: {failed}")
            
            return {
                'success': True,
                'totalCandidates': len(formatted_candidates),
                'scrapedAt': datetime.now().isoformat(),
                'candidates': formatted_candidates,
                'debug_info': { # Keeping debug info for reference, though user didn't ask explicitly allowed
                    'time_taken_seconds': round(duration, 2),
                    'total_failed': failed
                }
            }

    def _format_profile(self, data: Dict) -> Dict:
        """Map raw Naukri profile to desired output schema"""
        
        # Extract Education
        edu_list = data.get('educations', [])
        ug_data = {}
        pg_data = {}
        
        # Simple heuristic: First is usually Highest/PG, Last is UG? 
        # Or look for 'degree' field. 
        # Without seeing the content, we'll try to safe-guard.
        # Let's map indexes safely.
        
        if edu_list and isinstance(edu_list, list):
            # Try to find specific UG/PG markers if possible, otherwise mapped by index
            # For now, we'll just populate safely from the list
            if len(edu_list) > 0:
                # highest calc usually
                pass 
                
        # Extract Skills
        # mergedKeySkill is usually the display string
        skills = data.get('mergedKeySkill') or data.get('keywords')

        return {
            # ===== PERSONAL INFO =====
            'name': data.get('name'),
            'email': data.get('email'),
            'mobile': data.get('mobile'),
            'gender': data.get('gender'),
            'dateOfBirth': data.get('dateOfBirth') or data.get('birthDate'),
            'maritalStatus': data.get('maritalStatus'),
            
            # ===== LOCATION =====
            'currentLocation': data.get('currentLocation') or data.get('mailCity'),
            'permanentAddress': data.get('permanentAddress'),
            'preferredLocations': data.get('preferredLocations'),
            
            # ===== CURRENT EMPLOYMENT =====
            'currentDesignation': data.get('currentDesignation'),
            'currentCompany': data.get('currentCompany'),
            'currentRole': data.get('currentRole'),
            'functionalArea': data.get('functionalArea'),
            'industryType': data.get('industryType'),
            'employmentType': data.get('employmentType'),
            
            # ===== PREVIOUS EMPLOYMENT =====
            'previousDesignation': data.get('previousDesignation'),
            'previousCompany': data.get('previousCompany'),
            
            # ===== EXPERIENCE & COMPENSATION =====
            'totalExperience': data.get('totalExperience'),
            'currentCTC': data.get('currentCTC'),
            'expectedCTC': data.get('expectedCTC'),
            'noticePeriod': data.get('noticePeriod'),
            
            # ===== EDUCATION (Robust Extraction) =====
            # We treat the first education entry as the primary degree if specific keys missing
            'ugDegree': edu_list[0].get('degree') if edu_list else None,
            'ugSpecialization': edu_list[0].get('specialization') if edu_list else None,
            'ugInstitute': edu_list[0].get('institute') if edu_list else None,
            'ugYear': edu_list[0].get('year') if edu_list else None,
            
            'pgDegree': edu_list[1].get('degree') if len(edu_list) > 1 else None,
            'pgSpecialization': edu_list[1].get('specialization') if len(edu_list) > 1 else None,
            'pgInstitute': edu_list[1].get('institute') if len(edu_list) > 1 else None,
            'pgYear': edu_list[1].get('year') if len(edu_list) > 1 else None,
            
            # ===== SKILLS & PROFILE =====
            'keySkills': skills,
            'jobTitle': data.get('jobTitle'),
            'profileSummary': data.get('profileSummary') or data.get('summary'),
            
            # ===== PROFILE STATS =====
            'profileViews': data.get('profileViews'),
            'profileDownloads': data.get('profileDownloads'),
            
            # ===== CV (RAW TEXT) =====
            'cvAttached': data.get('cvAttached'),
            'textCv': data.get('textCv'),
            
            # ===== METADATA =====
            'profileLastModified': data.get('profileLastModified'),
            'profileLastActive': data.get('profileLastActive'),
            'scrapedAt': datetime.now().isoformat()
        }


# FastAPI App
app = FastAPI(title="Naukri Async Scraper")

@app.post("/scrape")
async def scrape_endpoint(input_data: ScraperInput):
    """
    Endpoint for Apify Actor.
    Each request spawns a new AsyncNaukriScraper instance.
    This ensures isolation between multiple users calling this endpoint simultaneously.
    """
    logger.info(f"Received scrape request. Max: {input_data.maxResults}")
    scraper = AsyncNaukriScraper(
        curl_command=input_data.curlCommand, 
        max_results=input_data.maxResults,
        concurrency=input_data.concurrency
    )
    return await scraper.run()

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
