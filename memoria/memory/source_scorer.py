import math
import re
import logging
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)

class SourceScorer:
    """Evaluates the credibility of information sources based on domain authority, recency, and consensus."""
    
    def __init__(self):
        # Regex patterns for domains
        self.official_patterns = [
            re.compile(r"^docs\..*"),
            re.compile(r"^.*\.readthedocs\.io"),
            re.compile(r"^github\.com/[^/]+/[^/]+/wiki"),
            re.compile(r"^.*\.gitbook\.io")
        ]
        
        self.official_domains = {
            "docs.python.org", "python.org", "w3.org", "ietf.org", "npmjs.com", "pypi.org",
            "crewai.com", "docs.crewai.com", "langchain.com", "python.langchain.com", "docs.langchain.com",
            "autogen-hub.github.io", "microsoft.github.io", "openapis.org", "neo4j.com"
        }
        
        self.major_blog_domains = {
            "medium.com", "towardsdatascience.com", "dev.to", "stackoverflow.com", "github.com",
            "hashnode.dev", "hashnode.com", "hackernoon.com", "reddit.com", "substack.com", "infoq.com"
        }

    def get_domain_authority(self, url: str) -> float:
        """Determines the baseline credibility weight based on domain classification."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Strip www.
            if domain.startswith("www."):
                domain = domain[4:]
                
            # Check official list/patterns
            if domain in self.official_domains:
                return 0.95
                
            for pattern in self.official_patterns:
                if pattern.match(domain):
                    return 0.95
                    
            # Check research papers
            if "arxiv" in domain or domain.endswith(".edu"):
                return 0.90
                
            # Check major blogs/communities
            if domain in self.major_blog_domains or any(blog in domain for blog in self.major_blog_domains):
                return 0.70
                
            # Unknown blogs/sites
            return 0.35
        except Exception as e:
            logger.warning(f"Error parsing domain authority for {url}: {e}")
            return 0.35

    def get_recency_decay(self, url: str, text: str = "") -> float:
        """Computes decay multiplier based on the age of the article.
        
        Decay formula: e^(-age_days / 365)
        """
        # Look for date patterns in URL (e.g. /2024/03/12/ or /2023-11-20/)
        date_patterns = [
            r"/(\d{4})/(\d{2})/(\d{2})/",
            r"/(\d{4})-(\d{2})-(\d{2})/",
            r"/(\d{4})/(\d{2})/"
        ]
        
        pub_date = None
        for pattern in date_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        pub_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    else:
                        # Year and month only
                        pub_date = datetime(int(match.group(1)), int(match.group(2)), 1)
                    break
                except ValueError:
                    pass
                    
        # If not in URL, try scanning text for common date markers
        if not pub_date and text:
            # Look for "Published on YYYY-MM-DD" or similar
            text_match = re.search(r"(?:published|updated|date|on)\s*(?:on|in)?\s*(\d{4})[-/](\d{2})[-/](\d{2})", text, re.IGNORECASE)
            if text_match:
                try:
                    pub_date = datetime(int(text_match.group(1)), int(text_match.group(2)), int(text_match.group(3)))
                except ValueError:
                    pass

        # Fallback: if no date is found, assume it is fresh (no decay)
        if not pub_date:
            return 1.0
            
        age_days = (datetime.now() - pub_date).days
        if age_days < 0:
            age_days = 0
            
        # e^(-age_days / 365)
        decay = math.exp(-age_days / 365.0)
        return max(0.1, decay)  # Cap decay floor at 0.1

    def score_source(self, url: str, text: str = "") -> float:
        """Combines domain authority and recency to calculate a single credibility weight."""
        authority = self.get_domain_authority(url)
        decay = self.get_recency_decay(url, text)
        score = authority * decay
        logger.info(f"Source score for {url}: {score:.3f} (auth: {authority}, decay: {decay:.3f})")
        return score

    @staticmethod
    def combine_confidences(confidences: list[float]) -> float:
        """Applies Cross-Source Agreement formula to boost consensus confidence.
        
        Formula: 1 - product(1 - confidence_i)
        """
        if not confidences:
            return 0.0
        prod = 1.0
        for c in confidences:
            prod *= (1.0 - min(0.99, max(0.0, c)))
        return round(1.0 - prod, 4)
