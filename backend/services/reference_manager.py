"""
Reference Manager - Track and format citations/references
Used for both verification and summarization to provide proper source attribution
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from collections import OrderedDict


class ReferenceManager:
    """
    Manages references and citations throughout verification/summarization
    Provides formatted references in various formats (APA, Chicago, Harvard)
    """

    def __init__(self):
        self.references: OrderedDict[str, Dict] = OrderedDict()  # ref_id -> reference data
        self.reference_count = 0

    def add_reference(
        self,
        title: str,
        url: str,
        source: str = "",
        accessed_from: str = "search",
        published_at: str = "",
        extra_info: Dict = None
    ) -> str:
        """
        Add a reference and return reference ID
        
        Args:
            title: Article/source title
            url: Source URL
            source: Domain/publisher name
            accessed_from: Where this came from (cache, search, api, input)
            published_at: Publication date
            extra_info: Additional metadata
        
        Returns:
            Reference ID (REF_001, REF_002, etc)
        """
        # Deduplicate by URL
        for ref_id, ref in self.references.items():
            if ref["url"] == url:
                return ref_id

        self.reference_count += 1
        ref_id = f"REF_{self.reference_count:03d}"

        self.references[ref_id] = {
            "ref_id": ref_id,
            "title": title,
            "url": url,
            "source": source or self._extract_domain(url),
            "accessed_from": accessed_from,
            "published_at": published_at,
            "accessed_at": datetime.now().isoformat(),
            "extra_info": extra_info or {},
        }

        return ref_id

    def get_reference(self, ref_id: str) -> Optional[Dict]:
        """Get a specific reference by ID"""
        return self.references.get(ref_id)

    def get_all_references(self) -> List[Dict]:
        """Get all references in order"""
        return list(self.references.values())

    def format_references(self, style: str = "harvard") -> str:
        """
        Format all references in specified style
        
        Args:
            style: "harvard", "apa", "chicago"
        
        Returns:
            Formatted references string
        """
        if not self.references:
            return "No references"

        lines = []

        if style == "harvard":
            lines.append("### References (Harvard Style)\n")
            for ref_id, ref in self.references.items():
                lines.append(self._format_harvard(ref_id, ref))

        elif style == "apa":
            lines.append("### References (APA Style)\n")
            for ref_id, ref in self.references.items():
                lines.append(self._format_apa(ref_id, ref))

        elif style == "chicago":
            lines.append("### References (Chicago Style)\n")
            for ref_id, ref in self.references.items():
                lines.append(self._format_chicago(ref_id, ref))

        else:  # Simple format
            lines.append("### References\n")
            for ref_id, ref in self.references.items():
                lines.append(self._format_simple(ref_id, ref))

        return "\n".join(lines)

    def format_inline_citation(self, ref_id: str) -> str:
        """Format inline citation for a reference"""
        if ref_id not in self.references:
            return f"[{ref_id}]"
        return f"[{ref_id}]"

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            return domain or "unknown"
        except:
            return "unknown"

    @staticmethod
    def _format_harvard(ref_id: str, ref: Dict) -> str:
        """Format reference in Harvard style"""
        domain = ref["source"]
        title = ref["title"]
        url = ref["url"]
        date = ref.get("published_at", "n.d.")
        
        return f"{ref_id}. {domain} ({date}). {title}. Retrieved from {url}"

    @staticmethod
    def _format_apa(ref_id: str, ref: Dict) -> str:
        """Format reference in APA style"""
        domain = ref["source"]
        title = ref["title"]
        url = ref["url"]
        date = ref.get("published_at", "n.d.")
        
        return f"{ref_id}. {domain}. ({date}). {title}. Retrieved from {url}"

    @staticmethod
    def _format_chicago(ref_id: str, ref: Dict) -> str:
        """Format reference in Chicago style"""
        domain = ref["source"]
        title = ref["title"]
        url = ref["url"]
        date = ref.get("published_at", "n.d.")
        
        return f"{ref_id}. {domain}. \"{title}.\" {date}. Accessed {url}"

    @staticmethod
    def _format_simple(ref_id: str, ref: Dict) -> str:
        """Format reference in simple style"""
        return f"{ref_id}. {ref['source']} - {ref['title']}\n{ref['url']}"

    def get_references_json(self) -> Dict:
        """Get all references as JSON"""
        return {
            "references": list(self.references.values()),
            "total_count": len(self.references),
        }

    def clear(self):
        """Clear all references"""
        self.references.clear()
        self.reference_count = 0

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "references": list(self.references.values()),
            "total_count": len(self.references),
        }


# Global reference manager instance
_reference_manager: Optional[ReferenceManager] = None


def get_reference_manager() -> ReferenceManager:
    """Get or create global reference manager"""
    global _reference_manager
    if _reference_manager is None:
        _reference_manager = ReferenceManager()
    return _reference_manager


def create_request_reference_manager() -> ReferenceManager:
    """Create a new reference manager for a specific request"""
    return ReferenceManager()
