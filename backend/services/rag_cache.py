"""
Corrective RAG System with Cache-First Strategy
1. Check cache for sufficient data
2. If insufficient, do Google search
3. Cache most frequent results
4. Use for verification with reference tracking
"""

import asyncio
import os
from typing import List, Dict, Tuple, Optional
try:
    from services.cache_manager import get_cache_manager
    from services.serp_news import search_related_news_from_query
    from services.reference_manager import get_reference_manager
except ModuleNotFoundError:
    from backend.services.cache_manager import get_cache_manager
    from backend.services.serp_news import search_related_news_from_query
    from backend.services.reference_manager import get_reference_manager

class CorrrectiveRAG:
    """
    Intelligent RAG system that:
    1. Checks cache first
    2. Falls back to SERP if cache insufficient
    3. Stores results in cache for future use
    """

    def __init__(self, cache_threshold_chars: int = 100):
        """
        Args:
            cache_threshold_chars: Minimum required cache data (OPTIMIZED: Reduced from 200)
        """
        self.cache_manager = get_cache_manager()
        self.reference_manager = get_reference_manager()
        self.cache_threshold = cache_threshold_chars
        self.search_timeout_sec = float(os.getenv("RAG_SEARCH_TIMEOUT_SEC", "2.5"))

    async def retrieve_evidence(
        self, 
        query: str, 
        max_results: int = 3,
        force_fresh: bool = False
    ) -> Dict:
        """
        Retrieve evidence for a claim using cache-first strategy
        
        Returns:
            {
                "evidence": [
                    {
                        "title": "...",
                        "snippet": "...",
                        "url": "...",
                        "source": "...",
                        "ref_id": "REF_001"  # For reference tracking
                    },
                    ...
                ],
                "source": "cache" | "search",
                "cache_info": {...}  # If from cache
            }
        """
        references = self.reference_manager
        
        # Step 1: Try cache first (unless forced fresh)
        if not force_fresh:
            cached = self.cache_manager.get(query)
            if cached:
                cached_results = cached.get("results", []) or []
                cached_news_data = (cached.get("news_data", "") or "").strip()
                results = cached_results[:max_results]
                has_sufficient_cache = (
                    len(cached_results) >= max_results
                    and len(cached_news_data) >= self.cache_threshold
                )
                
                if has_sufficient_cache:
                    # Register references
                    for result in results:
                        ref_id = references.add_reference(
                            title=result.get("title", ""),
                            url=result.get("url", ""),
                            source=result.get("source", ""),
                            accessed_from="cache"
                        )
                        result["ref_id"] = ref_id
                    
                    return {
                        "evidence": results,
                        "source": "cache",
                        "cache_info": cached.get("cached_info", {}),
                        "cache_stats": self.cache_manager.get_cache_stats()
                    }
        
        # Step 2: Cache miss or insufficient data - search
        try:
            search_results = await asyncio.wait_for(
                asyncio.to_thread(
                    search_related_news_from_query,
                    query,
                    max_results=max_results
                ),
                timeout=self.search_timeout_sec,
            )
        except Exception:
            search_results = []
        
        # Register references
        for i, result in enumerate(search_results):
            ref_id = references.add_reference(
                title=result.get("title", ""),
                url=result.get("url", ""),
                source=result.get("source", ""),
                accessed_from="search"
            )
            result["ref_id"] = ref_id
        
        # Step 3: Cache the results for future use
        combined_text = " ".join([
            result.get("description", "") 
            for result in search_results
        ])
        
        self.cache_manager.set(query, search_results, combined_text)
        
        return {
            "evidence": search_results,
            "source": "search",
            "cache_info": None,
            "cache_stats": self.cache_manager.get_cache_stats()
        }

    async def verify_with_rag(
        self,
        claim: str,
        max_results: int = 3
    ) -> Dict:
        """
        Verify a claim using RAG approach
        
        Returns:
            {
                "evidence": [...],
                "evidence_source": "cache" | "search",
                "references": [...],
                "cache_stats": {...}
            }
        """
        result = await self.retrieve_evidence(claim, max_results)
        
        return {
            "evidence": result["evidence"],
            "evidence_source": result["source"],
            "references": self.reference_manager.get_all_references(),
            "cache_stats": result.get("cache_stats", {})
        }

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache_manager.get_cache_stats()

    def clear_cache(self) -> Dict:
        """Clear all cache"""
        self.cache_manager.clear()
        return {"status": "Cache cleared", "stats": self.cache_manager.get_cache_stats()}


# Global RAG instance
_rag: Optional[CorrrectiveRAG] = None

def get_rag() -> CorrrectiveRAG:
    global _rag
    if _rag is None:
        _rag = CorrrectiveRAG()
    return _rag


def reset_rag():
    """Reset RAG instance (for testing)"""
    global _rag
    _rag = None
