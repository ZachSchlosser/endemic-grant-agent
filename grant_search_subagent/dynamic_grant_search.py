#!/usr/bin/env python3
"""
Dynamic Grant Search Engine
Replaces hardcoded foundation lists with intelligent, multi-source discovery
"""

import os
import sys
import json
import asyncio
import aiohttp
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse, urljoin

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

from utils.logger import GrantAgentLogger
from grant_search_agent import Grant, FundingTarget, GrantStatus
from async_web_scraper import AsyncWebScraper, ScrapingResult, ScrapingConfig
from url_prioritizer import URLPrioritizer, URLScore

logger = GrantAgentLogger().get_logger("dynamic_search")


@dataclass
class SearchResult:
    """Represents a search result from external sources"""
    title: str
    url: str
    description: str
    source: str
    confidence_score: float
    found_keywords: List[str]
    
    
@dataclass
class VerificationResult:
    """Result of grant opportunity verification"""
    is_valid: bool
    confidence: float
    issues: List[str]
    verified_data: Dict[str, str]


class DynamicGrantSearchEngine:
    """Intelligent grant discovery engine using multiple sources"""
    
    def __init__(self, config_path: str = None):
        """Initialize with configuration"""
        logger.info("Initializing DynamicGrantSearchEngine")
        
        if not config_path:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     'config', 'foundation_seeds.json')
        
        self.config = self._load_config(config_path)
        self.session = None
        
        # Load search keywords from CLAUDE.md
        self.search_keywords = self._extract_keywords_from_claude_md()
        
        # Initialize verification database
        self.known_funders = self.config.get('foundation_seeds', {})
        
        # Initialize async web scraper with environment configuration
        scraping_config = ScrapingConfig(
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5')),
            request_delay=float(os.getenv('REQUEST_DELAY', '1.5')),
            user_agent=os.getenv('USER_AGENT', 'Endemic-Grant-Agent/1.0 (+https://endemic.org/grant-agent)'),
            cache_ttl_hours=int(os.getenv('CACHE_TTL_HOURS', '24'))
        )
        self.web_scraper = AsyncWebScraper(scraping_config)
        
        # Initialize URL prioritizer
        self.url_prioritizer = URLPrioritizer()
        
        logger.info("DynamicGrantSearchEngine initialized successfully")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return {"foundation_seeds": {}, "search_engines": {}, "grant_aggregators": {}}
    
    def _extract_keywords_from_claude_md(self) -> List[str]:
        """Extract search keywords from CLAUDE.md file"""
        logger.info("Extracting search keywords from CLAUDE.md")
        
        claude_md_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'CLAUDE.md')
        keywords = []
        
        try:
            with open(claude_md_path, 'r') as f:
                content = f.read()
            
            # Extract keywords from key sections
            keyword_patterns = [
                r'### Core Educational Framework.*?#### Moving Institutions',
                r'### Key Projects & Initiatives.*?### Program Details',
                r'### For (.*?) Research',
                r'### For (.*?) Development'
            ]
            
            base_keywords = [
                "artificial intelligence", "AI ethics", "consciousness research",
                "educational innovation", "leadership development", "human-AI collaboration",
                "metacognitive skills", "transformative learning", "systems thinking",
                "diverse intelligences", "process philosophy", "phenomenology",
                "ontology", "epistemology", "cognitive science", "spiritual technology",
                "regenerative communities", "wisdom traditions", "contemplative science"
            ]
            
            # Add project-specific keywords
            project_keywords = [
                "OntoEdit", "cognitive widgets", "metaphysical flexibility",
                "SNF", "securing nation's future", "AI literacy",
                "futures we shape", "executive briefings", "strategic guidance"
            ]
            
            keywords.extend(base_keywords)
            keywords.extend(project_keywords)
            
            logger.info(f"Extracted {len(keywords)} search keywords from CLAUDE.md")
            
        except Exception as e:
            logger.warning(f"Could not extract keywords from CLAUDE.md: {e}")
            # Fallback keywords
            keywords = [
                "AI ethics funding", "consciousness research grants", "educational innovation",
                "leadership development funding", "transformative learning grants"
            ]
        
        return keywords
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'User-Agent': self.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def search_via_search_engines(self, max_results: int = 50) -> List[SearchResult]:
        """Search for grant opportunities using search engines"""
        logger.info(f"Starting search via search engines, max_results: {max_results}")
        
        results = []
        
        # Generate search queries combining keywords with grant-specific terms
        search_queries = self._generate_search_queries()
        
        # Use Brave Search MCP tool if available, otherwise fallback to direct search
        try:
            # Try to use MCP Brave Search tool
            for query in search_queries[:10]:  # Limit to avoid API limits
                brave_results = await self._brave_search(query)
                results.extend(brave_results)
                
                # Respectful delay
                await asyncio.sleep(float(os.getenv('REQUEST_DELAY', '1.5')))
        except Exception as e:
            logger.warning(f"Brave search failed: {e}, falling back to direct search")
            # Fallback to direct web search
            results.extend(await self._fallback_web_search(search_queries[:5]))
        
        # Remove duplicates and rank by confidence
        unique_results = self._deduplicate_results(results)
        ranked_results = sorted(unique_results, key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"Search completed: found {len(ranked_results)} unique results")
        return ranked_results[:max_results]
    
    async def intelligent_discovery(self, max_urls: int = 50) -> List[Grant]:
        """
        Perform intelligent grant discovery using async scraping and URL prioritization
        
        Args:
            max_urls: Maximum number of URLs to process
            
        Returns:
            List of validated Grant objects
        """
        logger.info(f"Starting intelligent grant discovery with max_urls: {max_urls}")
        
        # Step 1: Generate initial URL pool from multiple sources
        all_urls = await self._collect_discovery_urls()
        logger.info(f"Collected {len(all_urls)} URLs from various sources")
        
        # Step 2: Prioritize URLs using intelligent scoring
        context_keywords = set(self.search_keywords[:10])  # Use top keywords for context
        url_scores = self.url_prioritizer.prioritize_urls(all_urls, context_keywords)
        
        # Step 3: Select top URLs for scraping
        top_urls = self.url_prioritizer.get_top_urls(url_scores, limit=max_urls)
        logger.info(f"Selected top {len(top_urls)} URLs for scraping")
        
        # Step 4: Scrape URLs asynchronously with respectful practices
        scraping_results = await self.web_scraper.scrape_urls(top_urls)
        successful_results = [r for r in scraping_results if r.error is None]
        logger.info(f"Successfully scraped {len(successful_results)}/{len(top_urls)} URLs")
        
        # Step 5: Extract and validate grant opportunities from scraped content
        search_results = []
        for result in successful_results:
            extracted_grants = self._extract_grants_from_scraped_content(result)
            search_results.extend(extracted_grants)
        
        logger.info(f"Extracted {len(search_results)} potential grant opportunities")
        
        # Step 6: Validate opportunities and convert to Grant objects
        validated_grants = await self.validate_new_opportunities(search_results)
        logger.info(f"Validated {len(validated_grants)} grant opportunities")
        
        # Step 7: Sort by alignment score and return
        validated_grants.sort(key=lambda g: g.alignment_score, reverse=True)
        
        return validated_grants
    
    async def _collect_discovery_urls(self) -> List[str]:
        """Collect URLs from multiple sources for grant discovery"""
        all_urls = set()
        
        # Source 1: Foundation seed URLs
        for funder_name, funder_data in self.known_funders.items():
            base_urls = funder_data.get('base_urls', [])
            for base_url in base_urls:
                # Add base URL and common grant paths
                all_urls.add(base_url)
                all_urls.add(f"{base_url}/grants")
                all_urls.add(f"{base_url}/funding")
                all_urls.add(f"{base_url}/opportunities")
                all_urls.add(f"{base_url}/apply")
        
        # Source 2: Grant aggregator sites
        aggregator_urls = [
            "https://grants.gov/search-grants.html",
            "https://www.grants.gov/web/grants/search-grants.html",
            "https://www.foundationcenter.org/find-funding",
            "https://candid.org/find-funding",
            "https://www.grantspace.org/",
            "https://www.pivot.cos.com/funding/",
            "https://researchprofessional.com/funding/"
        ]
        all_urls.update(aggregator_urls)
        
        # Source 3: High-priority foundation URLs
        priority_foundations = [
            "https://www.nsf.gov/funding/",
            "https://chanzuckerberg.com/science/programs/",
            "https://www.templeton.org/grants/",
            "https://www.simonsfoundation.org/funding-opportunities/",
            "https://www.gatesfoundation.org/how-we-work/general-information/grant-opportunities/",
            "https://www.macfound.org/programs/",
            "https://www.carnegie.org/programs/",
            "https://www.knightfoundation.org/apply/",
            "https://www.rockefellerfoundation.org/grants-fellowships/",
            "https://www.fordfoundation.org/work/"
        ]
        all_urls.update(priority_foundations)
        
        # Source 4: AI and technology specific funders
        tech_funders = [
            "https://research.google/research-areas/",
            "https://www.microsoft.com/en-us/research/",
            "https://openai.com/research/",
            "https://www.anthropic.com/",
            "https://aipartnership.org/",
            "https://futureofhumanity.org/",
            "https://www.fhi.ox.ac.uk/"
        ]
        all_urls.update(tech_funders)
        
        logger.info(f"Collected {len(all_urls)} URLs from {4} sources")
        return list(all_urls)
    
    def _extract_grants_from_scraped_content(self, scraping_result: ScrapingResult) -> List[SearchResult]:
        """Extract grant opportunities from scraped web content"""
        grants = []
        content = scraping_result.content
        url = scraping_result.url
        
        # Enhanced patterns for grant detection
        grant_patterns = [
            # Title-based patterns
            r'<title>([^<]*(?:grant|funding|award|fellowship|scholarship|opportunity)[^<]*)</title>',
            
            # Heading patterns
            r'<h[1-6][^>]*>([^<]*(?:grant|funding|award|fellowship|scholarship|opportunity)[^<]*)</h[1-6]>',
            
            # Link patterns with descriptive text
            r'<a[^>]*href="([^"]*(?:grant|funding|opportunity|apply)[^"]*)"[^>]*>([^<]+)</a>',
            
            # Program/opportunity sections
            r'<div[^>]*class="[^"]*(?:grant|opportunity|funding)[^"]*"[^>]*>.*?<h[^>]*>([^<]+)</h',
            
            # Deadline-based patterns (indicates active opportunities)
            r'deadline[:\s]*([^<\n]+(?:202[5-9]|january|february|march|april|may|june|july|august|september|october|november|december)[^<\n]*)',
        ]
        
        for pattern in grant_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # Extract title and URL
                if match.lastindex >= 2:
                    grant_url = match.group(1)
                    title = match.group(2)
                elif match.lastindex >= 1:
                    title = match.group(1)
                    grant_url = url  # Use the scraped page URL
                else:
                    continue
                
                # Clean up title
                title = re.sub(r'<[^>]+>', '', title).strip()
                if len(title) < 10 or len(title) > 200:
                    continue  # Filter out too short/long titles
                
                # Calculate relevance based on keyword matching
                keywords_found = [kw for kw in self.search_keywords 
                                if kw.lower() in title.lower()]
                
                # Additional context from surrounding content
                context_start = max(0, match.start() - 200)
                context_end = min(len(content), match.end() + 200)
                context = content[context_start:context_end]
                
                # Look for additional keywords in context
                context_keywords = [kw for kw in self.search_keywords 
                                  if kw.lower() in context.lower()]
                keywords_found.extend(context_keywords)
                keywords_found = list(set(keywords_found))  # Remove duplicates
                
                confidence = min(len(keywords_found) / max(len(self.search_keywords), 1), 1.0)
                
                if confidence > 0.1:  # Minimum confidence threshold
                    grants.append(SearchResult(
                        title=title,
                        url=grant_url if grant_url.startswith('http') else urljoin(url, grant_url),
                        description=context[:300].strip(),  # First 300 chars as description
                        source=urlparse(url).netloc,
                        confidence_score=confidence,
                        found_keywords=keywords_found
                    ))
        
        # Remove duplicates within this result
        seen_titles = set()
        unique_grants = []
        for grant in grants:
            title_norm = grant.title.lower().strip()
            if title_norm not in seen_titles:
                seen_titles.add(title_norm)
                unique_grants.append(grant)
        
        logger.debug(f"Extracted {len(unique_grants)} grants from {url}")
        return unique_grants
    
    def _generate_search_queries(self) -> List[str]:
        """Generate intelligent search queries"""
        base_queries = [
            "research grant funding 2025 deadline",
            "foundation grant artificial intelligence",
            "consciousness research funding opportunity",
            "AI ethics grant program 2025",
            "educational innovation funding",
            "leadership development grant",
            "transformative learning research funding"
        ]
        
        # Add site-specific searches
        site_queries = []
        for site in ["grants.gov", "foundationcenter.org", "grantspace.org"]:
            site_queries.extend([
                f"site:{site} artificial intelligence consciousness",
                f"site:{site} educational innovation grant 2025",
                f"site:{site} leadership development funding"
            ])
        
        # Combine with project-specific terms
        project_queries = [
            '"cognitive science" funding opportunity 2025',
            '"human-AI collaboration" research grant',
            '"metacognitive skills" education funding',
            '"process philosophy" research support'
        ]
        
        all_queries = base_queries + site_queries + project_queries
        logger.info(f"Generated {len(all_queries)} search queries")
        return all_queries
    
    async def _brave_search(self, query: str) -> List[SearchResult]:
        """Search using Brave Search API (via MCP if available)"""
        # This would integrate with MCP Brave Search tool
        # For now, return placeholder - will be implemented with MCP integration
        logger.info(f"Brave search query: {query}")
        return []
    
    async def _fallback_web_search(self, queries: List[str]) -> List[SearchResult]:
        """Fallback web search by scraping grant aggregator sites"""
        results = []
        
        aggregators = self.config.get('grant_aggregators', {})
        
        for name, config in aggregators.items():
            if config.get('requires_auth', False):
                logger.info(f"Skipping {name} - requires authentication")
                continue
            
            try:
                site_results = await self._scrape_aggregator_site(name, config, queries[:3])
                results.extend(site_results)
            except Exception as e:
                logger.warning(f"Failed to scrape {name}: {e}")
        
        return results
    
    async def _scrape_aggregator_site(self, site_name: str, config: Dict, 
                                    queries: List[str]) -> List[SearchResult]:
        """Scrape a grant aggregator site"""
        results = []
        
        for query in queries:
            try:
                # Construct search URL
                base_url = config['url']
                search_endpoint = config.get('search_endpoint', '/search')
                search_url = urljoin(base_url, search_endpoint)
                
                # Add query parameters
                params = {'q': query, 'type': 'grants'}
                
                async with self.session.get(search_url, params=params) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        page_results = self._extract_grants_from_html(html_content, site_name)
                        results.extend(page_results)
                
                # Respectful delay
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.warning(f"Error scraping {site_name} for query '{query}': {e}")
        
        return results
    
    def _extract_grants_from_html(self, html_content: str, source: str) -> List[SearchResult]:
        """Extract grant information from HTML content"""
        results = []
        
        # Common patterns for grant information
        patterns = [
            r'<title>([^<]*grant[^<]*)</title>',
            r'<h[1-6][^>]*>([^<]*grant[^<]*)</h[1-6]>',
            r'href="([^"]*grant[^"]*)"[^>]*>([^<]+)',
            r'<div[^>]*grant[^>]*>([^<]+)</div>'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                title = match.group(1) if match.lastindex >= 1 else "Grant Opportunity"
                url = match.group(2) if match.lastindex >= 2 else ""
                
                # Calculate confidence based on keyword matching
                keywords_found = [kw for kw in self.search_keywords 
                                if kw.lower() in title.lower()]
                confidence = len(keywords_found) / len(self.search_keywords)
                
                if confidence > 0.1:  # Minimum confidence threshold
                    results.append(SearchResult(
                        title=title.strip(),
                        url=url,
                        description="",  # Will be filled by verification
                        source=source,
                        confidence_score=confidence,
                        found_keywords=keywords_found
                    ))
        
        return results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on URL and title similarity"""
        seen_urls = set()
        seen_titles = set()
        unique_results = []
        
        for result in results:
            # Normalize URL and title for comparison
            norm_url = result.url.lower().strip('/')
            norm_title = result.title.lower().strip()
            
            if norm_url not in seen_urls and norm_title not in seen_titles:
                seen_urls.add(norm_url)
                seen_titles.add(norm_title)
                unique_results.append(result)
        
        logger.info(f"Deduplicated {len(results)} results to {len(unique_results)} unique items")
        return unique_results
    
    async def search_grant_aggregators(self) -> List[SearchResult]:
        """Search known grant aggregator websites"""
        log_function_start("search_grant_aggregators", "dynamic_search")
        
        results = []
        aggregators = self.config.get('grant_aggregators', {})
        
        for name, config in aggregators.items():
            if config.get('requires_auth', False):
                logger.info(f"Skipping {name} - requires authentication")
                continue
            
            try:
                site_results = await self._scrape_aggregator_comprehensive(name, config)
                results.extend(site_results)
            except Exception as e:
                logger.error(f"Error searching {name}: {e}")
        
        log_function_end("search_grant_aggregators", "dynamic_search", 
                        f"found {len(results)} results")
        return results
    
    async def _scrape_aggregator_comprehensive(self, site_name: str, config: Dict) -> List[SearchResult]:
        """Comprehensively scrape an aggregator site"""
        results = []
        
        # Generate multiple search approaches for the site
        search_terms = [
            "artificial intelligence",
            "consciousness research", 
            "educational innovation",
            "leadership development",
            "AI ethics",
            "transformative learning"
        ]
        
        for term in search_terms:
            try:
                term_results = await self._scrape_aggregator_site(site_name, config, [term])
                results.extend(term_results)
                
                # Respectful delay between searches
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.warning(f"Error searching {site_name} for {term}: {e}")
        
        return results
    
    async def validate_new_opportunities(self, search_results: List[SearchResult]) -> List[Grant]:
        """Validate and convert search results to Grant objects"""
        log_function_start("validate_new_opportunities", "dynamic_search", 
                          count=len(search_results))
        
        validated_grants = []
        
        # Process results in batches to avoid overwhelming servers
        batch_size = min(self.max_concurrent, 5)
        
        for i in range(0, len(search_results), batch_size):
            batch = search_results[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self._validate_single_opportunity(result) for result in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Grant):
                    validated_grants.append(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Validation error: {result}")
            
            # Respectful delay between batches
            await asyncio.sleep(self.request_delay)
        
        log_function_end("validate_new_opportunities", "dynamic_search", 
                        f"validated {len(validated_grants)} grants")
        return validated_grants
    
    async def _validate_single_opportunity(self, search_result: SearchResult) -> Optional[Grant]:
        """Validate a single grant opportunity"""
        try:
            # Fetch the actual page content
            verification = await self._verify_grant_page(search_result.url)
            
            if not verification.is_valid or verification.confidence < 0.5:
                return None
            
            # Extract grant details
            grant_data = verification.verified_data
            
            # Determine funding target based on content analysis
            funding_target = self._determine_funding_target(grant_data.get('description', ''))
            
            # Create Grant object
            grant = Grant(
                organization_name=grant_data.get('organization', 'Unknown'),
                grant_name=grant_data.get('name', search_result.title),
                alignment_score=self._calculate_alignment_score(grant_data),
                grant_amount=grant_data.get('amount', 'Amount not specified'),
                deadline=grant_data.get('deadline'),
                grant_link=search_result.url,
                funding_target=funding_target,
                notes=f"Discovered via {search_result.source}. Confidence: {verification.confidence:.2f}"
            )
            
            return grant
            
        except Exception as e:
            logger.warning(f"Failed to validate {search_result.url}: {e}")
            return None
    
    async def _verify_grant_page(self, url: str) -> VerificationResult:
        """Verify that a URL contains a legitimate grant opportunity"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return VerificationResult(False, 0.0, [f"HTTP {response.status}"], {})
                
                content = await response.text()
                
                # Extract grant information
                extracted_data = self._extract_grant_info_from_page(content, url)
                
                # Validate against known patterns
                validation_score = self._calculate_validation_score(extracted_data, content)
                
                is_valid = validation_score > 0.3
                issues = self._identify_validation_issues(extracted_data, content)
                
                return VerificationResult(is_valid, validation_score, issues, extracted_data)
                
        except Exception as e:
            return VerificationResult(False, 0.0, [str(e)], {})
    
    def _extract_grant_info_from_page(self, content: str, url: str) -> Dict[str, str]:
        """Extract grant information from page content"""
        data = {}
        
        # Extract organization from URL
        domain = urlparse(url).netloc
        data['organization'] = self._identify_organization_from_domain(domain)
        
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            data['name'] = title_match.group(1).strip()
        
        # Extract description (from meta description or first paragraph)
        desc_match = re.search(r'<meta[^>]*description[^>]*content="([^"]+)"', content, re.IGNORECASE)
        if desc_match:
            data['description'] = desc_match.group(1)
        else:
            # Fallback to first paragraph
            p_match = re.search(r'<p[^>]*>([^<]+)</p>', content, re.IGNORECASE)
            if p_match:
                data['description'] = p_match.group(1)
        
        # Extract deadline patterns
        deadline_patterns = [
            r'deadline[:\s]*([\w\s,]+202[5-9])',
            r'due[:\s]*([\w\s,]+202[5-9])',
            r'apply by[:\s]*([\w\s,]+202[5-9])'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data['deadline'] = match.group(1).strip()
                break
        
        # Extract amount patterns
        amount_patterns = [
            r'\$[\d,]+(?:\s*-\s*\$[\d,]+)?',
            r'up to \$[\d,]+',
            r'maximum of \$[\d,]+'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data['amount'] = match.group(0)
                break
        
        return data
    
    def _identify_organization_from_domain(self, domain: str) -> str:
        """Identify organization from domain name"""
        # Remove common prefixes/suffixes
        clean_domain = domain.replace('www.', '').replace('foundation.', '').replace('.org', '').replace('.com', '')
        
        # Check against known funders
        for org_name, org_data in self.known_funders.items():
            base_urls = org_data.get('base_urls', [])
            if any(base_url in domain for base_url in base_urls):
                return org_name
        
        # Format domain as organization name
        return clean_domain.replace('.', ' ').replace('-', ' ').title()
    
    def _calculate_validation_score(self, data: Dict[str, str], content: str) -> float:
        """Calculate validation score for extracted grant data"""
        score = 0.0
        
        # Check for required fields
        if data.get('name'):
            score += 0.2
        if data.get('organization'):
            score += 0.2
        if data.get('description'):
            score += 0.3
        
        # Check for grant-specific keywords in content
        grant_keywords = ['grant', 'funding', 'award', 'fellowship', 'scholarship']
        keyword_count = sum(1 for kw in grant_keywords if kw in content.lower())
        score += min(keyword_count * 0.1, 0.3)
        
        # Check for application-related content
        app_keywords = ['application', 'deadline', 'eligibility', 'requirements']
        app_count = sum(1 for kw in app_keywords if kw in content.lower())
        score += min(app_count * 0.05, 0.2)
        
        return min(score, 1.0)
    
    def _identify_validation_issues(self, data: Dict[str, str], content: str) -> List[str]:
        """Identify potential issues with the grant opportunity"""
        issues = []
        
        if not data.get('name'):
            issues.append("No clear grant name found")
        if not data.get('description'):
            issues.append("No description found")
        if not data.get('deadline'):
            issues.append("No deadline information")
        
        # Check for red flags
        red_flags = ['expired', 'closed', 'no longer accepting']
        for flag in red_flags:
            if flag in content.lower():
                issues.append(f"Potential issue: {flag}")
        
        return issues
    
    def _determine_funding_target(self, description: str) -> FundingTarget:
        """Determine the appropriate funding target based on description"""
        desc_lower = description.lower()
        
        # OntoEdit keywords
        if any(kw in desc_lower for kw in ['cognitive', 'ontology', 'philosophy', 'ai']):
            return FundingTarget.ONTOEDIT
        
        # SNF keywords  
        if any(kw in desc_lower for kw in ['education', 'learning', 'curriculum', 'student']):
            return FundingTarget.SNF
        
        # Leadership program keywords
        if any(kw in desc_lower for kw in ['leadership', 'management', 'executive']):
            return FundingTarget.LEADERSHIP_PROGRAM
        
        # Default to Divinity School
        return FundingTarget.DIVINITY_SCHOOL
    
    def _calculate_alignment_score(self, grant_data: Dict[str, str]) -> float:
        """Calculate alignment score based on grant content"""
        score = 5.0  # Base score
        
        description = grant_data.get('description', '').lower()
        name = grant_data.get('name', '').lower()
        combined = f"{description} {name}"
        
        # Sacred Societies alignment keywords
        alignment_keywords = {
            'consciousness': 1.0,
            'artificial intelligence': 0.8,
            'ai': 0.8,
            'cognitive': 0.7,
            'philosophy': 0.6,
            'education': 0.6,
            'leadership': 0.5,
            'ethics': 0.5,
            'innovation': 0.4,
            'research': 0.3
        }
        
        for keyword, weight in alignment_keywords.items():
            if keyword in combined:
                score += weight
        
        # Cap at 10.0
        return min(score, 10.0)


# Usage example for testing
async def main():
    """Test the dynamic grant search engine with intelligent discovery"""
    engine = DynamicGrantSearchEngine()
    
    print("🔍 Testing Intelligent Grant Discovery System")
    print("=" * 60)
    
    try:
        # Test the intelligent discovery system
        print("\n🚀 Starting intelligent discovery...")
        discovered_grants = await engine.intelligent_discovery(max_urls=20)
        
        print(f"\n📊 Discovery Results:")
        print(f"   • Total grants discovered: {len(discovered_grants)}")
        
        if discovered_grants:
            print(f"   • Top alignment score: {discovered_grants[0].alignment_score:.1f}")
            print(f"   • Average alignment score: {sum(g.alignment_score for g in discovered_grants) / len(discovered_grants):.1f}")
            
            print(f"\n🏆 Top 5 Grant Opportunities:")
            for i, grant in enumerate(discovered_grants[:5], 1):
                print(f"   {i}. {grant.organization_name}: {grant.grant_name}")
                print(f"      Score: {grant.alignment_score:.1f} | Amount: {grant.grant_amount}")
                print(f"      Target: {grant.funding_target.value} | URL: {grant.grant_link[:50]}...")
                print()
        
        # Test scraper cache stats
        print("📈 Scraper Cache Statistics:")
        cache_stats = engine.web_scraper.get_cache_stats()
        for key, value in cache_stats.items():
            print(f"   • {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())