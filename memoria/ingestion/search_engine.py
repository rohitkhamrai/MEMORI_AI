import os
import logging
from abc import ABC, abstractmethod
import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

class SearchProvider(ABC):
    """Abstract base class for all search providers."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[str]:
        """Executes search and returns a list of result URLs.
        
        Args:
            query: The search query string.
            max_results: Max URLs to return.
            
        Returns:
            list[str]: List of URLs.
        """
        pass


class DuckDuckGoProvider(SearchProvider):
    """DuckDuckGo Search Provider (Keyless/Free)."""
    
    def search(self, query: str, max_results: int = 5) -> list[str]:
        try:
            logger.info(f"Searching DuckDuckGo for: '{query}'")
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                if not results:
                    return []
                urls = [r["href"] for r in results if "href" in r]
                return urls[:max_results]
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []


class BraveProvider(SearchProvider):
    """Brave Search Provider (Paid API)."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.endpoint = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, max_results: int = 5) -> list[str]:
        if not self.api_key:
            logger.debug("Brave API Key not provided. Skipping Brave Provider.")
            return []
            
        try:
            logger.info(f"Searching Brave for: '{query}'")
            headers = {"X-Subscription-Token": self.api_key, "Accept": "application/json"}
            params = {"q": query, "count": max_results}
            
            response = httpx.get(self.endpoint, headers=headers, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("web", {}).get("results", [])
            urls = [r["url"] for r in results if "url" in r]
            return urls[:max_results]
        except Exception as e:
            logger.warning(f"Brave search failed: {e}")
            return []


class SerperProvider(SearchProvider):
    """Serper.dev Google Search Provider (Paid API)."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.endpoint = "https://google.serper.dev/search"

    def search(self, query: str, max_results: int = 5) -> list[str]:
        if not self.api_key:
            logger.debug("Serper API Key not provided. Skipping Serper Provider.")
            return []
            
        try:
            logger.info(f"Searching Serper for: '{query}'")
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
            payload = {"q": query, "num": max_results}
            
            response = httpx.post(self.endpoint, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("organic", [])
            urls = [r["link"] for r in results if "link" in r]
            return urls[:max_results]
        except Exception as e:
            logger.warning(f"Serper search failed: {e}")
            return []


class TavilyProvider(SearchProvider):
    """Tavily Search Provider (AI Search API)."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.endpoint = "https://api.tavily.com/search"

    def search(self, query: str, max_results: int = 5) -> list[str]:
        if not self.api_key:
            logger.debug("Tavily API Key not provided. Skipping Tavily Provider.")
            return []
            
        try:
            logger.info(f"Searching Tavily for: '{query}'")
            payload = {"api_key": self.api_key, "query": query, "max_results": max_results}
            
            response = httpx.post(self.endpoint, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            urls = [r["url"] for r in results if "url" in r]
            return urls[:max_results]
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")
            return []


class SearchEngine:
    """Orchestrates search providers in priority order, falling back down to DuckDuckGo."""
    
    def __init__(self):
        # Build priority list of providers based on available keys
        self.providers: list[SearchProvider] = []
        
        # Load paid APIs first if key exists
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            self.providers.append(TavilyProvider(tavily_key))
            
        serper_key = os.getenv("SERPER_API_KEY")
        if serper_key:
            self.providers.append(SerperProvider(serper_key))
            
        brave_key = os.getenv("BRAVE_API_KEY")
        if brave_key:
            self.providers.append(BraveProvider(brave_key))
            
        # DuckDuckGo is always the fallback provider at the end
        self.providers.append(DuckDuckGoProvider())

    def query(self, query: str, max_results: int = 5) -> list[str]:
        """Searches using the highest priority working provider."""
        for provider in self.providers:
            urls = provider.search(query, max_results=max_results)
            if urls:
                logger.info(f"Search successful using {provider.__class__.__name__}. Found {len(urls)} results.")
                return urls
        logger.error("All search providers failed or returned no results.")
        return []
