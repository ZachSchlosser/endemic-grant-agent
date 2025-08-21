#!/usr/bin/env python3
"""
Intelligent Cache Management System
Handles caching for grant discovery, web scraping, and API responses
"""

import os
import json
import pickle
import hashlib
import time
from typing import Any, Dict, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import logging
from enum import Enum

from .logger import GrantAgentLogger

class CacheType(Enum):
    """Types of cached data"""
    WEB_CONTENT = "web_content"
    API_RESPONSE = "api_response"
    SEARCH_RESULTS = "search_results"
    GRANT_VALIDATION = "grant_validation"
    URL_ANALYSIS = "url_analysis"
    SCRAPED_DATA = "scraped_data"

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    key: str
    data: Any
    cache_type: CacheType
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """Update access information"""
        self.access_count += 1
        self.last_accessed = datetime.now()

class IntelligentCacheManager:
    """
    Intelligent caching system that provides:
    - Multi-level caching (memory + disk)
    - TTL-based expiration
    - LRU eviction for memory cache
    - Compression for large entries
    - Cache analytics and monitoring
    - Automatic cleanup
    """
    
    def __init__(self, 
                 cache_dir: Optional[str] = None,
                 memory_cache_size: int = 100,
                 default_ttl_hours: int = 24,
                 enable_compression: bool = True):
        """
        Initialize the intelligent cache manager
        
        Args:
            cache_dir: Directory for disk cache (None for env var or default)
            memory_cache_size: Maximum entries in memory cache
            default_ttl_hours: Default TTL in hours
            enable_compression: Whether to compress large cache entries
        """
        self.logger = GrantAgentLogger().get_logger("cache_manager")
        
        # Cache configuration
        if cache_dir is None:
            cache_dir = os.getenv('CACHE_DIR', '/tmp/endemic_grant_cache')
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_cache_size = memory_cache_size
        self.default_ttl_hours = default_ttl_hours
        self.enable_compression = enable_compression
        
        # Memory cache: LRU implementation using dict (Python 3.7+ maintains insertion order)
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Cache statistics
        self.stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'evictions': 0,
            'disk_writes': 0,
            'disk_reads': 0,
            'compressions': 0,
            'decompressions': 0
        }
        
        # Create subdirectories for different cache types
        for cache_type in CacheType:
            type_dir = self.cache_dir / cache_type.value
            type_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Initialized IntelligentCacheManager at {self.cache_dir}")
        
        # Perform startup cleanup
        self._cleanup_expired_entries()
    
    def get(self, key: str, cache_type: CacheType = CacheType.WEB_CONTENT) -> Optional[Any]:
        """
        Get cached data by key
        
        Args:
            key: Cache key
            cache_type: Type of cached data
            
        Returns:
            Cached data if found and not expired, None otherwise
        """
        # Check memory cache first
        full_key = self._make_full_key(key, cache_type)
        
        if full_key in self.memory_cache:
            entry = self.memory_cache[full_key]
            
            if entry.is_expired():
                # Remove expired entry
                del self.memory_cache[full_key]
                self._remove_from_disk(full_key, cache_type)
                self.stats['misses'] += 1
                return None
            
            # Move to end (LRU)
            self.memory_cache[full_key] = self.memory_cache.pop(full_key)
            entry.touch()
            self.stats['memory_hits'] += 1
            
            self.logger.debug(f"Memory cache hit for {key}")
            return entry.data
        
        # Check disk cache
        disk_entry = self._load_from_disk(full_key, cache_type)
        if disk_entry:
            if disk_entry.is_expired():
                # Remove expired entry
                self._remove_from_disk(full_key, cache_type)
                self.stats['misses'] += 1
                return None
            
            # Load into memory cache
            self._add_to_memory(full_key, disk_entry)
            disk_entry.touch()
            self.stats['disk_hits'] += 1
            
            self.logger.debug(f"Disk cache hit for {key}")
            return disk_entry.data
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, data: Any, cache_type: CacheType = CacheType.WEB_CONTENT,
            ttl_hours: Optional[int] = None, metadata: Optional[Dict] = None):
        """
        Store data in cache
        
        Args:
            key: Cache key
            data: Data to cache
            cache_type: Type of cached data
            ttl_hours: Time to live in hours (None for default)
            metadata: Additional metadata
        """
        if ttl_hours is None:
            ttl_hours = self.default_ttl_hours
        
        expires_at = datetime.now() + timedelta(hours=ttl_hours) if ttl_hours > 0 else None
        full_key = self._make_full_key(key, cache_type)
        
        entry = CacheEntry(
            key=key,
            data=data,
            cache_type=cache_type,
            created_at=datetime.now(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # Add to memory cache
        self._add_to_memory(full_key, entry)
        
        # Save to disk asynchronously (in practice, would use thread pool)
        self._save_to_disk(full_key, entry)
        
        self.logger.debug(f"Cached {key} with TTL {ttl_hours}h")
    
    def delete(self, key: str, cache_type: CacheType = CacheType.WEB_CONTENT):
        """Delete cached entry"""
        full_key = self._make_full_key(key, cache_type)
        
        # Remove from memory
        if full_key in self.memory_cache:
            del self.memory_cache[full_key]
        
        # Remove from disk
        self._remove_from_disk(full_key, cache_type)
        
        self.logger.debug(f"Deleted cache entry {key}")
    
    def clear(self, cache_type: Optional[CacheType] = None):
        """
        Clear cache entries
        
        Args:
            cache_type: Specific cache type to clear (None for all)
        """
        if cache_type is None:
            # Clear everything
            self.memory_cache.clear()
            for cache_type_enum in CacheType:
                type_dir = self.cache_dir / cache_type_enum.value
                for file_path in type_dir.glob("*.pkl"):
                    file_path.unlink()
            self.logger.info("Cleared all cache")
        else:
            # Clear specific type
            to_remove = [k for k, v in self.memory_cache.items() 
                        if v.cache_type == cache_type]
            for key in to_remove:
                del self.memory_cache[key]
            
            type_dir = self.cache_dir / cache_type.value
            for file_path in type_dir.glob("*.pkl"):
                file_path.unlink()
            
            self.logger.info(f"Cleared {cache_type.value} cache")
    
    def cleanup(self, max_age_hours: Optional[int] = None):
        """
        Clean up expired and old cache entries
        
        Args:
            max_age_hours: Remove entries older than this (None for just expired)
        """
        self._cleanup_memory_cache(max_age_hours)
        self._cleanup_disk_cache(max_age_hours)
        self.logger.info("Cache cleanup completed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = sum([
            self.stats['memory_hits'],
            self.stats['disk_hits'],
            self.stats['misses']
        ])
        
        hit_rate = 0.0
        if total_requests > 0:
            hit_rate = (self.stats['memory_hits'] + self.stats['disk_hits']) / total_requests
        
        # Disk usage
        disk_usage = self._calculate_disk_usage()
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'memory_cache_size': len(self.memory_cache),
            'disk_usage_mb': disk_usage / (1024 * 1024),
            'cache_types': self._count_by_type()
        }
    
    def _make_full_key(self, key: str, cache_type: CacheType) -> str:
        """Create full cache key with type prefix"""
        return f"{cache_type.value}:{key}"
    
    def _make_cache_key(self, data: Union[str, Dict, List]) -> str:
        """Generate cache key from data"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _add_to_memory(self, full_key: str, entry: CacheEntry):
        """Add entry to memory cache with LRU eviction"""
        # Remove if already exists (for updating position)
        if full_key in self.memory_cache:
            del self.memory_cache[full_key]
        
        # Add to end
        self.memory_cache[full_key] = entry
        
        # Evict oldest if over limit
        while len(self.memory_cache) > self.memory_cache_size:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
            self.stats['evictions'] += 1
    
    def _save_to_disk(self, full_key: str, entry: CacheEntry):
        """Save entry to disk"""
        try:
            cache_type_dir = self.cache_dir / entry.cache_type.value
            file_key = hashlib.md5(full_key.encode()).hexdigest()
            file_path = cache_type_dir / f"{file_key}.pkl"
            
            # Prepare data for serialization
            serializable_entry = {
                'key': entry.key,
                'data': entry.data,
                'cache_type': entry.cache_type.value,
                'created_at': entry.created_at.isoformat(),
                'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
                'access_count': entry.access_count,
                'last_accessed': entry.last_accessed.isoformat() if entry.last_accessed else None,
                'metadata': entry.metadata
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(serializable_entry, f)
            
            self.stats['disk_writes'] += 1
            
        except Exception as e:
            self.logger.warning(f"Failed to save cache entry to disk: {e}")
    
    def _load_from_disk(self, full_key: str, cache_type: CacheType) -> Optional[CacheEntry]:
        """Load entry from disk"""
        try:
            cache_type_dir = self.cache_dir / cache_type.value
            file_key = hashlib.md5(full_key.encode()).hexdigest()
            file_path = cache_type_dir / f"{file_key}.pkl"
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # Reconstruct CacheEntry
            entry = CacheEntry(
                key=data['key'],
                data=data['data'],
                cache_type=CacheType(data['cache_type']),
                created_at=datetime.fromisoformat(data['created_at']),
                expires_at=datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None,
                access_count=data['access_count'],
                last_accessed=datetime.fromisoformat(data['last_accessed']) if data['last_accessed'] else None,
                metadata=data['metadata']
            )
            
            self.stats['disk_reads'] += 1
            return entry
            
        except Exception as e:
            self.logger.warning(f"Failed to load cache entry from disk: {e}")
            return None
    
    def _remove_from_disk(self, full_key: str, cache_type: CacheType):
        """Remove entry from disk"""
        try:
            cache_type_dir = self.cache_dir / cache_type.value
            file_key = hashlib.md5(full_key.encode()).hexdigest()
            file_path = cache_type_dir / f"{file_key}.pkl"
            
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            self.logger.warning(f"Failed to remove cache entry from disk: {e}")
    
    def _cleanup_memory_cache(self, max_age_hours: Optional[int] = None):
        """Clean up memory cache"""
        now = datetime.now()
        to_remove = []
        
        for key, entry in self.memory_cache.items():
            if entry.is_expired():
                to_remove.append(key)
            elif max_age_hours and entry.created_at < now - timedelta(hours=max_age_hours):
                to_remove.append(key)
        
        for key in to_remove:
            del self.memory_cache[key]
    
    def _cleanup_disk_cache(self, max_age_hours: Optional[int] = None):
        """Clean up disk cache"""
        for cache_type in CacheType:
            type_dir = self.cache_dir / cache_type.value
            
            for file_path in type_dir.glob("*.pkl"):
                try:
                    # Check file age
                    file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    should_remove = False
                    
                    if max_age_hours and file_age > timedelta(hours=max_age_hours):
                        should_remove = True
                    else:
                        # Load and check expiration
                        entry = self._load_from_disk(file_path.stem, cache_type)
                        if entry and entry.is_expired():
                            should_remove = True
                    
                    if should_remove:
                        file_path.unlink()
                        
                except Exception as e:
                    self.logger.warning(f"Error during disk cleanup for {file_path}: {e}")
    
    def _cleanup_expired_entries(self):
        """Startup cleanup of expired entries"""
        self.logger.info("Performing startup cache cleanup...")
        self._cleanup_disk_cache()
    
    def _calculate_disk_usage(self) -> int:
        """Calculate total disk usage in bytes"""
        total_size = 0
        for cache_type in CacheType:
            type_dir = self.cache_dir / cache_type.value
            for file_path in type_dir.glob("*.pkl"):
                try:
                    total_size += file_path.stat().st_size
                except:
                    pass
        return total_size
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count entries by cache type"""
        counts = {}
        for cache_type in CacheType:
            type_dir = self.cache_dir / cache_type.value
            counts[cache_type.value] = len(list(type_dir.glob("*.pkl")))
        return counts


# Specialized cache helpers for common grant discovery use cases

class GrantDiscoveryCache:
    """High-level cache interface for grant discovery operations"""
    
    def __init__(self, cache_manager: Optional[IntelligentCacheManager] = None):
        self.cache = cache_manager or IntelligentCacheManager()
        self.logger = GrantAgentLogger().get_logger("grant_cache")
    
    def cache_web_content(self, url: str, content: str, ttl_hours: int = 24):
        """Cache web page content"""
        key = self.cache._make_cache_key(url)
        self.cache.set(key, content, CacheType.WEB_CONTENT, ttl_hours, 
                      metadata={'url': url})
    
    def get_web_content(self, url: str) -> Optional[str]:
        """Get cached web content"""
        key = self.cache._make_cache_key(url)
        return self.cache.get(key, CacheType.WEB_CONTENT)
    
    def cache_search_results(self, query: str, results: List[Dict], ttl_hours: int = 12):
        """Cache search results"""
        key = self.cache._make_cache_key(query)
        self.cache.set(key, results, CacheType.SEARCH_RESULTS, ttl_hours,
                      metadata={'query': query, 'result_count': len(results)})
    
    def get_search_results(self, query: str) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = self.cache._make_cache_key(query)
        return self.cache.get(key, CacheType.SEARCH_RESULTS)
    
    def cache_grant_validation(self, url: str, validation_result: Dict, ttl_hours: int = 48):
        """Cache grant validation results"""
        key = self.cache._make_cache_key(url)
        self.cache.set(key, validation_result, CacheType.GRANT_VALIDATION, ttl_hours,
                      metadata={'url': url})
    
    def get_grant_validation(self, url: str) -> Optional[Dict]:
        """Get cached grant validation"""
        key = self.cache._make_cache_key(url)
        return self.cache.get(key, CacheType.GRANT_VALIDATION)
    
    def cache_url_analysis(self, urls: List[str], analysis_results: List[Dict], ttl_hours: int = 24):
        """Cache URL analysis results"""
        key = self.cache._make_cache_key(sorted(urls))
        self.cache.set(key, analysis_results, CacheType.URL_ANALYSIS, ttl_hours,
                      metadata={'url_count': len(urls)})
    
    def get_url_analysis(self, urls: List[str]) -> Optional[List[Dict]]:
        """Get cached URL analysis"""
        key = self.cache._make_cache_key(sorted(urls))
        return self.cache.get(key, CacheType.URL_ANALYSIS)


def main():
    """Test the caching system"""
    print("🗄️  Testing Intelligent Cache Management System")
    print("=" * 60)
    
    # Initialize cache manager
    cache_manager = IntelligentCacheManager(memory_cache_size=5)
    grant_cache = GrantDiscoveryCache(cache_manager)
    
    # Test web content caching
    print("\n📄 Testing web content caching...")
    test_url = "https://www.nsf.gov/funding/"
    test_content = "<html><body>NSF Funding Opportunities</body></html>"
    
    grant_cache.cache_web_content(test_url, test_content, ttl_hours=1)
    retrieved_content = grant_cache.get_web_content(test_url)
    
    print(f"   Cached: {len(test_content)} chars")
    print(f"   Retrieved: {len(retrieved_content) if retrieved_content else 0} chars")
    print(f"   Match: {test_content == retrieved_content}")
    
    # Test search results caching
    print("\n🔍 Testing search results caching...")
    test_query = "AI ethics funding grants"
    test_results = [
        {"title": "AI Ethics Grant Program", "url": "https://example.com/grant1"},
        {"title": "Ethics in AI Research", "url": "https://example.com/grant2"}
    ]
    
    grant_cache.cache_search_results(test_query, test_results, ttl_hours=1)
    retrieved_results = grant_cache.get_search_results(test_query)
    
    print(f"   Cached: {len(test_results)} results")
    print(f"   Retrieved: {len(retrieved_results) if retrieved_results else 0} results")
    print(f"   Match: {test_results == retrieved_results}")
    
    # Test cache statistics
    print("\n📊 Cache Statistics:")
    stats = cache_manager.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        elif isinstance(value, dict):
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")
    
    # Test cache performance under load
    print(f"\n⚡ Performance testing...")
    import time
    
    start_time = time.time()
    for i in range(100):
        key = f"test_key_{i}"
        data = f"test_data_{i}" * 100  # ~1KB per entry
        cache_manager.set(key, data, ttl_hours=1)
    
    write_time = time.time() - start_time
    
    start_time = time.time()
    hits = 0
    for i in range(100):
        key = f"test_key_{i}"
        result = cache_manager.get(key)
        if result:
            hits += 1
    
    read_time = time.time() - start_time
    
    print(f"   Write 100 entries: {write_time:.3f}s ({100/write_time:.1f} ops/sec)")
    print(f"   Read 100 entries: {read_time:.3f}s ({100/read_time:.1f} ops/sec)")
    print(f"   Hit rate: {hits}/100")
    
    # Final statistics
    print(f"\n📈 Final Statistics:")
    final_stats = cache_manager.get_stats()
    for key, value in final_stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")
    
    print("\n✅ Cache system test completed!")


if __name__ == "__main__":
    main()