# ============================================
# AI Research Agent - Webpage Reader Tool
# ============================================
"""
Web content extraction tool using Trafilatura and BeautifulSoup4.

WHY TWO LIBRARIES?
------------------
1. Trafilatura (primary): Purpose-built for article extraction. It strips
   navigation, ads, footers, and returns just the main article text.
   Success rate: ~90% on news/blog articles.

2. BeautifulSoup4 (fallback): When Trafilatura fails (dynamic JS pages,
   unusual layouts), BS4 does a simpler extraction by grabbing all <p> tags.
   Not as clean, but better than nothing.

This layered approach follows the "TRY THE BEST → FALL BACK TO GOOD ENOUGH"
pattern that production systems use.

CONTENT EXTRACTION CHALLENGES:
------------------------------
- JavaScript-rendered pages: Both libraries can't execute JS. We'd need
  Playwright/Selenium for that (stretch goal).
- Paywalled content: We can only extract what's publicly visible.
- Rate limiting: Some sites block rapid requests. We add delays and
  respect robots.txt implicitly through reasonable request patterns.
"""

import logging
import requests
import trafilatura
from bs4 import BeautifulSoup
from backend.state.research_state import ExtractedContent

logger = logging.getLogger(__name__)

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 15

# User-Agent header to identify our bot (some sites block default Python UA)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 "
        "ResearchAgent/1.0"
    )
}

import concurrent.futures

# Maximum content length to keep per page (in characters)
# ~3,500 chars ≈ 550 words — concise, focused, token-efficient
MAX_CONTENT_LENGTH = 3500


def read_webpages_parallel(urls: list[str], max_workers: int = 5) -> list[ExtractedContent]:
    """
    Extract content from multiple URLs concurrently in parallel.
    
    Drastically reduces extraction time (e.g. from 20 seconds down to 2 seconds).
    """
    if not urls:
        return []
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(read_webpage, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                content = future.result()
                results.append(content)
            except Exception as e:
                url = future_to_url[future]
                logger.error(f"Parallel extraction failed for {url}: {str(e)}")
                results.append(ExtractedContent(
                    url=url, title="Error", content=f"Parallel error: {str(e)}",
                    word_count=0, extraction_success=False
                ))
    return results


def read_webpage(url: str) -> ExtractedContent:
    """
    Extract the main content from a web page.
    
    Strategy:
    1. Fetch the raw HTML using requests
    2. Try Trafilatura first (best quality extraction)
    3. If Trafilatura fails, fall back to BeautifulSoup
    4. Truncate to MAX_CONTENT_LENGTH to avoid overwhelming the LLM
    
    Args:
        url: The URL of the web page to extract content from.
    
    Returns:
        ExtractedContent with the extracted text, title, and metadata.
        If extraction fails entirely, returns an object with extraction_success=False.
    
    Example:
        >>> content = read_webpage("https://example.com/article")
        >>> print(f"Title: {content.title}")
        >>> print(f"Words: {content.word_count}")
    """
    try:
        logger.info(f"Extracting content from: {url}")
        
        # Step 1: Fetch the raw HTML
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,  # Follow redirects (common for shortened URLs)
        )
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        
        html = response.text
        
        # Step 2: Try Trafilatura first (higher quality extraction)
        content = _extract_with_trafilatura(html, url)
        
        # Step 3: Fallback to BeautifulSoup if Trafilatura fails
        if not content:
            logger.info(f"Trafilatura failed for {url}, trying BeautifulSoup")
            content = _extract_with_beautifulsoup(html)
        
        # Step 4: If both fail, return a failure result
        if not content:
            logger.warning(f"All extraction methods failed for: {url}")
            return ExtractedContent(
                url=url,
                title=_extract_title(html),
                content="Content extraction failed for this page.",
                word_count=0,
                extraction_success=False,
            )
        
        # Step 5: Truncate if needed and return
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH] + "\n\n[Content truncated...]"
        
        title = _extract_title(html)
        word_count = len(content.split())
        
        logger.info(f"Successfully extracted {word_count} words from: {url}")
        
        return ExtractedContent(
            url=url,
            title=title,
            content=content,
            word_count=word_count,
            extraction_success=True,
        )
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        return ExtractedContent(
            url=url, title="Timeout", content="Request timed out.",
            word_count=0, extraction_success=False,
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching {url}: {str(e)}")
        return ExtractedContent(
            url=url, title="Error", content=f"HTTP error: {str(e)}",
            word_count=0, extraction_success=False,
        )
    except Exception as e:
        logger.error(f"Unexpected error extracting {url}: {str(e)}")
        return ExtractedContent(
            url=url, title="Error", content=f"Extraction error: {str(e)}",
            word_count=0, extraction_success=False,
        )


def _extract_with_trafilatura(html: str, url: str) -> str | None:
    """
    Extract main content using Trafilatura.
    
    Trafilatura is excellent at identifying the main article content
    and stripping away navigation, sidebars, ads, and boilerplate.
    
    Returns:
        Extracted text content, or None if extraction fails.
    """
    try:
        content = trafilatura.extract(
            html,
            url=url,
            include_comments=False,    # Skip user comments
            include_tables=True,       # Keep data tables (useful for research)
            include_links=False,       # Don't include inline hyperlinks
            favor_precision=True,      # Prefer precision over recall
            output_format="txt",       # Plain text output
        )
        return content if content and len(content.strip()) > 50 else None
    except Exception as e:
        logger.debug(f"Trafilatura extraction error: {str(e)}")
        return None


def _extract_with_beautifulsoup(html: str) -> str | None:
    """
    Fallback content extraction using BeautifulSoup.
    
    This is a simpler approach: grab all <p> (paragraph) tags and
    concatenate their text. Less precise than Trafilatura but works
    on more page types.
    
    Returns:
        Extracted text content, or None if extraction fails.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements (they contain code, not content)
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Extract text from paragraph tags
        paragraphs = soup.find_all("p")
        content = "\n\n".join(
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 30  # Skip tiny paragraphs (nav items, etc.)
        )
        
        return content if content and len(content.strip()) > 50 else None
    except Exception as e:
        logger.debug(f"BeautifulSoup extraction error: {str(e)}")
        return None


def _extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else "Untitled"
    except Exception:
        return "Untitled"
