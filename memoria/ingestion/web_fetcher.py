import logging
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WebFetcher:
    """Fetches web page content and cleans it to plain text."""
    
    def __init__(self, timeout_seconds: float = 10.0, max_retries: int = 2):
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(self, url: str) -> str:
        """Fetches raw HTML from a URL and extracts clean body text.
        
        Args:
            url: The HTTP/HTTPS URL to fetch.
            
        Returns:
            str: Clean text representation of the webpage.
        """
        client = httpx.Client(headers=self.headers, timeout=self.timeout, follow_redirects=True)
        html_content = ""
        
        for attempt in range(self.max_retries + 1):
            try:
                response = client.get(url)
                response.raise_for_status()
                html_content = response.text
                break
            except Exception as e:
                if attempt == self.max_retries:
                    logger.warning(f"Failed to fetch {url} after {self.max_retries} retries: {e}")
                    return ""
                logger.info(f"Retry fetching {url} (attempt {attempt + 1}/{self.max_retries}) due to: {e}")
        
        if not html_content:
            return ""
            
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove scripts, styles, nav, footer, header
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
                
            # Get text and clean up whitespace
            text = soup.get_text(separator=" ")
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)
            
            return clean_text
        except Exception as e:
            logger.error(f"Failed parsing HTML from {url}: {e}")
            return ""
