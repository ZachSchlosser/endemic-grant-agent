#!/usr/bin/env python3
"""
Asynchronous Web Scraper for Grant Discovery
Implements respectful, rate-limited web scraping with caching and retry logic
"""

import asyncio
import aiohttp
import time
import random
from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import logging
import os
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import GrantAgentLogger
from utils.cache_manager import IntelligentCacheManager, CacheType, GrantDiscoveryCache

@dataclass
class ScrapingResult:
    """Result from web scraping operation"""
    url: str
    content: str
    status_code: int
    headers: Dict[str, str]
    scraped_at: datetime
    error: Optional[str] = None

@dataclass
class ScrapingConfig:
    """Configuration for web scraping behavior"""
    max_concurrent_requests: int = 5
    request_delay: float = 1.5
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0
    user_agent: str = "Endemic-Grant-Agent/1.0 (+https://endemic.org/grant-agent)"
    respect_robots_txt: bool = True
    cache_ttl_hours: int = 24
    max_content_size: int = 5 * 1024 * 1024  # 5MB

class AsyncWebScraper:
    """
    Asynchronous web scraper with respectful practices:
    - Rate limiting and delays
    - Robots.txt compliance
    - Caching to reduce server load
    - User-Agent identification
    - Graceful error handling
    - Retry logic with exponential backoff
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize the async web scraper"""
        self.config = config or ScrapingConfig()
        self.logger = GrantAgentLogger().get_logger("async_scraper")
        
        # Load config from environment
        self.config.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', self.config.max_concurrent_requests))
        self.config.request_delay = float(os.getenv('REQUEST_DELAY', self.config.request_delay))
        self.config.cache_ttl_hours = int(os.getenv('CACHE_TTL_HOURS', self.config.cache_ttl_hours))
        self.config.user_agent = os.getenv('USER_AGENT', self.config.user_agent)
        
        # Initialize intelligent caching system
        cache_dir = os.getenv('CACHE_DIR', '/tmp/endemic_grant_cache')
        self.cache_manager = IntelligentCacheManager(
            cache_dir=cache_dir,
            memory_cache_size=50,  # Keep frequently accessed pages in memory
            default_ttl_hours=self.config.cache_ttl_hours
        )
        self.grant_cache = GrantDiscoveryCache(self.cache_manager)
        
        # Track robots.txt files and rate limiting
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.last_request_time: Dict[str, float] = {}
        self.request_count: Dict[str, int] = {}
        
        # Initialize semaphore for concurrent request limiting
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        self.logger.info(f"Initialized AsyncWebScraper with {self.config.max_concurrent_requests} max concurrent requests")
    
    async def scrape_urls(self, urls: List[str]) -> List[ScrapingResult]:
        """
        Scrape multiple URLs asynchronously with respectful practices
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            List of ScrapingResult objects
        """
        self.logger.info(f"Starting async scraping of {len(urls)} URLs")
        
        # Create session with proper configuration
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrent_requests,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.config.user_agent}
        ) as session:
            
            # Create scraping tasks
            tasks = []
            for url in urls:
                task = asyncio.create_task(self._scrape_single_url(session, url))
                tasks.append(task)
            
            # Execute all tasks and gather results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            scraping_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Exception scraping {urls[i]}: {result}")
                    scraping_results.append(ScrapingResult(
                        url=urls[i],
                        content="",
                        status_code=0,
                        headers={},
                        scraped_at=datetime.now(),
                        error=str(result)
                    ))
                else:
                    scraping_results.append(result)
        
        successful = len([r for r in scraping_results if r.error is None])
        self.logger.info(f"Completed scraping: {successful}/{len(urls)} successful")
        
        return scraping_results
    
    async def _scrape_single_url(self, session: aiohttp.ClientSession, url: str) -> ScrapingResult:
        """
        Scrape a single URL with all respectful practices applied
        
        Args:
            session: aiohttp session
            url: URL to scrape
            
        Returns:
            ScrapingResult object
        """
        # Check intelligent cache first
        cached_content = self.grant_cache.get_web_content(url)
        if cached_content:
            self.logger.debug(f"Using cached result for {url}")
            return ScrapingResult(
                url=url,
                content=cached_content,
                status_code=200,
                headers={},
                scraped_at=datetime.now(),
                error=None
            )
        
        # Acquire semaphore to limit concurrent requests
        async with self.semaphore:
            
            # Check robots.txt compliance
            if not await self._can_fetch(url):
                self.logger.warning(f"Robots.txt disallows fetching {url}")
                return ScrapingResult(
                    url=url,
                    content="",
                    status_code=403,
                    headers={},
                    scraped_at=datetime.now(),
                    error="Blocked by robots.txt"
                )
            
            # Apply rate limiting
            await self._apply_rate_limiting(url)
            
            # Perform the actual request with retries
            for attempt in range(self.config.max_retries):
                try:
                    start_time = time.time()
                    
                    async with session.get(url) as response:
                        # Check content size
                        content_length = response.headers.get('content-length')
                        if content_length and int(content_length) > self.config.max_content_size:
                            raise ValueError(f"Content too large: {content_length} bytes")
                        
                        # Read content with size limit
                        content = await response.text()
                        if len(content.encode('utf-8')) > self.config.max_content_size:
                            content = content[:self.config.max_content_size // 2]  # Truncate if too large
                        
                        request_time = time.time() - start_time
                        
                        result = ScrapingResult(
                            url=url,
                            content=content,
                            status_code=response.status,
                            headers=dict(response.headers),
                            scraped_at=datetime.now()
                        )
                        
                        self.logger.debug(f"Scraped {url} in {request_time:.2f}s, status {response.status}, {len(content)} chars")
                        
                        # Cache successful results using intelligent cache
                        if response.status == 200:
                            self.grant_cache.cache_web_content(
                                url, 
                                content, 
                                ttl_hours=self.config.cache_ttl_hours
                            )
                        
                        return result
                        
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {self.config.timeout}s"
                    self.logger.warning(f"Timeout scraping {url} (attempt {attempt + 1})")
                    
                except aiohttp.ClientError as e:
                    error_msg = f"Client error: {str(e)}"
                    self.logger.warning(f"Client error scraping {url} (attempt {attempt + 1}): {e}")
                    
                except Exception as e:
                    error_msg = f"Unexpected error: {str(e)}"
                    self.logger.warning(f"Unexpected error scraping {url} (attempt {attempt + 1}): {e}")
                
                # Wait before retrying (exponential backoff)
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
            
            # All retries failed
            self.logger.error(f"Failed to scrape {url} after {self.config.max_retries} attempts")
            return ScrapingResult(
                url=url,
                content="",
                status_code=0,
                headers={},
                scraped_at=datetime.now(),
                error=error_msg
            )
    
    async def _can_fetch(self, url: str) -> bool:
        """
        Check if we can fetch the URL according to robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            True if allowed to fetch, False otherwise
        """
        if not self.config.respect_robots_txt:
            return True
        
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Check cache for robots.txt
        if base_url not in self.robots_cache:
            robots_url = urljoin(base_url, '/robots.txt')
            
            try:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[base_url] = rp
                self.logger.debug(f"Loaded robots.txt for {base_url}")
                
            except Exception as e:
                self.logger.warning(f"Could not load robots.txt for {base_url}: {e}")
                # If we can't load robots.txt, assume we can fetch
                return True
        
        # Check if we can fetch the URL
        rp = self.robots_cache.get(base_url)
        if rp:
            can_fetch = rp.can_fetch(self.config.user_agent, url)
            if not can_fetch:
                self.logger.debug(f"robots.txt disallows {url}")
            return can_fetch
        
        return True
    
    async def _apply_rate_limiting(self, url: str):
        """
        Apply rate limiting to respect server resources
        
        Args:
            url: URL being requested
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        current_time = time.time()
        
        # Check if we need to wait based on last request to this domain
        if domain in self.last_request_time:
            time_since_last = current_time - self.last_request_time[domain]
            if time_since_last < self.config.request_delay:
                wait_time = self.config.request_delay - time_since_last
                self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)
        
        # Update last request time
        self.last_request_time[domain] = time.time()
        
        # Track request count for logging
        self.request_count[domain] = self.request_count.get(domain, 0) + 1
    
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache"""
        try:
            cache_stats = self.cache_manager.get_stats()
            return {
                **cache_stats,
                'request_count_by_domain': dict(self.request_count)
            }
        except Exception as e:
            self.logger.warning(f"Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """
        Clear cache files
        
        Args:
            older_than_hours: Only clear files older than this many hours (None = clear all)
        """
        try:
            if older_than_hours:
                self.cache_manager.cleanup(max_age_hours=older_than_hours)
            else:
                self.cache_manager.clear(CacheType.WEB_CONTENT)
            
            self.logger.info(f"Cache clearing completed")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")


async def main():
    """Test the async web scraper"""
    # Test URLs
    test_urls = [
        'https://www.nsf.gov/funding/',
        'https://www.templeton.org/',
        'https://chanzuckerberg.com/science/',
        'https://www.simonsfoundation.org/funding-opportunities/'
    ]
    
    # Initialize scraper with test config
    config = ScrapingConfig(
        max_concurrent_requests=3,
        request_delay=2.0,
        timeout=15
    )
    
    scraper = AsyncWebScraper(config)
    
    print("Testing async web scraper...")
    print(f"Scraping {len(test_urls)} URLs with respectful practices")
    
    start_time = time.time()
    results = await scraper.scrape_urls(test_urls)
    total_time = time.time() - start_time
    
    print(f"\nResults after {total_time:.2f} seconds:")
    for result in results:
        status = "✅ Success" if result.error is None else f"❌ Error: {result.error}"
        content_preview = result.content[:100].replace('\n', ' ') if result.content else ""
        print(f"  {result.url}")
        print(f"    Status: {result.status_code} - {status}")
        print(f"    Content: {len(result.content)} chars - {content_preview}...")
        print()
    
    # Show cache stats
    print("Cache Statistics:")
    stats = scraper.get_cache_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())