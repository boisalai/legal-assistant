"""
CAIJ Search Service (Centre d'accès à l'information juridique du Québec)

Playwright-based implementation for scraping search results.
"""

import asyncio
import time
import os
from typing import List, Optional
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from models.caij_models import CAIJResult, CAIJSearchRequest, CAIJSearchResponse, CAIJCredentials, infer_rubrique
from config.settings import settings


class RateLimiter:
    """Simple rate limiter to respect CAIJ servers."""

    def __init__(self, max_requests: int = 10, time_window_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            max_requests: Maximum number of requests
            time_window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.requests = []

    async def wait_if_needed(self):
        """Wait if the request limit is reached."""
        now = time.time()
        window_start = now - self.time_window

        # Clean old requests
        self.requests = [req_time for req_time in self.requests if req_time > window_start]

        # If limit reached, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] - window_start + 1  # +1 for margin
            print(f"⏳ Rate limit reached, pausing for {sleep_time:.1f}s...")
            await asyncio.sleep(sleep_time)

            # Re-clean after waiting
            now = time.time()
            window_start = now - self.time_window
            self.requests = [req_time for req_time in self.requests if req_time > window_start]

        # Record this request
        self.requests.append(now)


class CAIJSearchService:
    """CAIJ search service with Playwright."""

    def __init__(self, credentials: Optional[CAIJCredentials] = None, headless: bool = True):
        """
        Initialize the CAIJ service.

        Args:
            credentials: CAIJ credentials (email/password)
            headless: Run browser in headless mode
        """
        # Get credentials from env if not provided
        if credentials is None:
            email = os.getenv("CAIJ_EMAIL")
            password = os.getenv("CAIJ_PASSWORD")
            if not email or not password:
                raise ValueError(
                    "Missing CAIJ credentials! "
                    "Set CAIJ_EMAIL and CAIJ_PASSWORD in .env or pass credentials as parameter"
                )
            credentials = CAIJCredentials(email=email, password=password)

        self.credentials = credentials
        self.headless = headless

        # Playwright session
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.authenticated = False

        # Rate limiting (10 req/min by default)
        self.rate_limiter = RateLimiter(max_requests=10, time_window_seconds=60)

    async def initialize(self):
        """Initialize the Playwright session and browser."""
        if self.browser is not None:
            return  # Already initialized

        print("🚀 Initializing CAIJ session...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100 if not self.headless else 0
        )

        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        self.page = await self.context.new_page()
        print("✅ Session initialized")

    async def close(self):
        """Close the Playwright session."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self.authenticated = False

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        print("🔚 CAIJ session closed")

    async def authenticate(self):
        """Authenticate on CAIJ."""
        if self.authenticated:
            return  # Already authenticated

        if not self.page:
            await self.initialize()

        print("🔐 CAIJ authentication...")

        try:
            # Navigate to login page
            await self.page.goto("https://app.caij.qc.ca", timeout=30000)
            await self.page.wait_for_load_state("networkidle")

            # Step 1: Email
            email_input = await self.page.wait_for_selector("#identifier", timeout=10000)
            await email_input.fill(self.credentials.email)

            continue_button = await self.page.wait_for_selector("button:has-text('Continuer')", timeout=5000)
            await continue_button.click()
            await self.page.wait_for_timeout(2000)

            # Step 2: Password
            password_input = await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            await password_input.fill(self.credentials.password)
            await password_input.press("Enter")

            # Wait for navigation
            await self.page.wait_for_url(
                lambda url: "connexion" not in url.lower() and "login" not in url.lower(),
                timeout=15000
            )
            await self.page.wait_for_load_state("networkidle", timeout=15000)

            # Close TOS popup if present
            try:
                close_button = await self.page.wait_for_selector('button[class*="close"]', timeout=3000)
                await close_button.click()
                await self.page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass  # No popup

            self.authenticated = True
            print("✅ Authentication successful")

        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            # Error screenshot
            if self.page:
                await self.page.screenshot(path="caij_auth_error.png")
            raise

    async def search(self, request: CAIJSearchRequest) -> CAIJSearchResponse:
        """
        Perform a search on CAIJ.

        Args:
            request: Search request

        Returns:
            Response with results
        """
        start_time = time.time()

        # Ensure authenticated
        if not self.authenticated:
            await self.authenticate()

        # Rate limiting
        await self.rate_limiter.wait_if_needed()

        print(f"🔎 CAIJ search: '{request.query}' (max {request.max_results} results)")

        try:
            # Always return to home page to reset search field
            # This avoids issues with multiple searches
            await self.page.goto("https://app.caij.qc.ca/fr", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=20000)
            await self.page.wait_for_timeout(1500)

            # Close popup if present
            try:
                close_button = await self.page.wait_for_selector('button[class*="close"]', timeout=2000)
                await close_button.click()
                await self.page.wait_for_timeout(500)
            except:
                pass

            # Find search field (increased timeout for multiple searches)
            search_input = self.page.get_by_placeholder("Rechercher dans tout le contenu")
            await search_input.wait_for(timeout=20000)

            # Fill and submit
            await search_input.fill(request.query)
            await search_input.press("Enter")

            # Wait for results (increased timeout for multiple searches)
            await self.page.wait_for_timeout(3000)
            await self.page.wait_for_selector('div[class*="result"]', timeout=20000)

            # Extract results
            results = await self._extract_results(request.max_results)

            execution_time = time.time() - start_time

            response = CAIJSearchResponse(
                query=request.query,
                results=results,
                total_found=len(results),
                timestamp=datetime.now(),
                execution_time_seconds=round(execution_time, 2)
            )

            print(f"✅ {len(results)} results extracted in {execution_time:.2f}s")

            return response

        except Exception as e:
            print(f"❌ Search error: {e}")
            # Error screenshot
            if self.page:
                await self.page.screenshot(path="caij_search_error.png")
            raise

    async def _extract_results(self, max_results: int) -> List[CAIJResult]:
        """
        Extract search results from the current page.

        Args:
            max_results: Maximum number of results to extract

        Returns:
            List of results
        """
        result_elements = await self.page.query_selector_all('div[class*="result"]')

        results = []
        for i, element in enumerate(result_elements[:max_results]):
            try:
                # Title
                title = "N/A"
                title_el = await element.query_selector('.section-title')
                if not title_el:
                    title_el = await element.query_selector('h2, h3, h4')
                if title_el:
                    title = await title_el.text_content()

                # URL
                url = None
                link = await element.query_selector('a[href]')
                if link:
                    href = await link.get_attribute('href')
                    if href and not href.startswith('http'):
                        url = f"https://app.caij.qc.ca{href}"
                    elif href:
                        url = href

                # Document type
                doc_type = "N/A"
                type_el = await element.query_selector('.doc-type')
                if type_el:
                    doc_type = await type_el.text_content()

                # Date
                date = "N/A"
                date_el = await element.query_selector('.date')
                if date_el:
                    date = await date_el.text_content()

                # Source
                source = "N/A"
                breadcrumb_el = await element.query_selector('.breadcrumb-item')
                if breadcrumb_el:
                    source = await breadcrumb_el.text_content()

                # Excerpt
                excerpt = "N/A"
                excerpt_el = await element.query_selector('.section-excerpt, .excerpt')
                if excerpt_el:
                    excerpt_text = await excerpt_el.text_content()
                    excerpt = excerpt_text.strip()[:500]  # Limit to 500 chars

                # Clean data
                clean_title = title.strip() if title != "N/A" else "N/A"
                clean_url = url if url else "N/A"
                clean_doc_type = doc_type.strip() if doc_type != "N/A" else "N/A"
                clean_source = source.strip() if source != "N/A" else "N/A"
                clean_date = date.strip() if date != "N/A" else "N/A"

                # Infer category
                rubrique = infer_rubrique(
                    document_type=clean_doc_type,
                    source=clean_source,
                    url=clean_url
                )

                # Create result
                result = CAIJResult(
                    title=clean_title,
                    url=clean_url,
                    document_type=clean_doc_type,
                    rubrique=rubrique,
                    source=clean_source,
                    date=clean_date,
                    excerpt=excerpt
                )

                results.append(result)

            except Exception as e:
                print(f"  ⚠️  Error extracting result #{i+1}: {e}")
                continue

        return results

    async def __aenter__(self):
        """Support async context manager."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Automatically close on context manager exit."""
        await self.close()
