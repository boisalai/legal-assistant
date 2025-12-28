"""
Service de recherche CAIJ (Centre d'accès à l'information juridique du Québec)

Implémentation basée sur Playwright pour scraping des résultats de recherche.
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
    """Rate limiter simple pour respecter les serveurs CAIJ."""

    def __init__(self, max_requests: int = 10, time_window_seconds: int = 60):
        """
        Initialiser le rate limiter.

        Args:
            max_requests: Nombre maximum de requêtes
            time_window_seconds: Fenêtre de temps en secondes
        """
        self.max_requests = max_requests
        self.time_window = time_window_seconds
        self.requests = []

    async def wait_if_needed(self):
        """Attendre si la limite de requêtes est atteinte."""
        now = time.time()
        window_start = now - self.time_window

        # Nettoyer les anciennes requêtes
        self.requests = [req_time for req_time in self.requests if req_time > window_start]

        # Si limite atteinte, attendre
        if len(self.requests) >= self.max_requests:
            sleep_time = self.requests[0] - window_start + 1  # +1 pour marge
            print(f"⏳ Rate limit atteint, pause de {sleep_time:.1f}s...")
            await asyncio.sleep(sleep_time)

            # Re-nettoyer après l'attente
            now = time.time()
            window_start = now - self.time_window
            self.requests = [req_time for req_time in self.requests if req_time > window_start]

        # Enregistrer cette requête
        self.requests.append(now)


class CAIJSearchService:
    """Service de recherche sur CAIJ avec Playwright."""

    def __init__(self, credentials: Optional[CAIJCredentials] = None, headless: bool = True):
        """
        Initialiser le service CAIJ.

        Args:
            credentials: Credentials CAIJ (email/password)
            headless: Exécuter le navigateur en mode headless
        """
        # Credentials depuis env si non fournis
        if credentials is None:
            email = os.getenv("CAIJ_EMAIL")
            password = os.getenv("CAIJ_PASSWORD")
            if not email or not password:
                raise ValueError(
                    "CAIJ credentials manquants! "
                    "Définir CAIJ_EMAIL et CAIJ_PASSWORD dans .env ou passer credentials en paramètre"
                )
            credentials = CAIJCredentials(email=email, password=password)

        self.credentials = credentials
        self.headless = headless

        # Session Playwright
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.authenticated = False

        # Rate limiting (10 req/min par défaut)
        self.rate_limiter = RateLimiter(max_requests=10, time_window_seconds=60)

    async def initialize(self):
        """Initialiser la session Playwright et le navigateur."""
        if self.browser is not None:
            return  # Déjà initialisé

        print("🚀 Initialisation de la session CAIJ...")

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
        print("✅ Session initialisée")

    async def close(self):
        """Fermer la session Playwright."""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            self.authenticated = False

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        print("🔚 Session CAIJ fermée")

    async def authenticate(self):
        """Authentifier sur CAIJ."""
        if self.authenticated:
            return  # Déjà authentifié

        if not self.page:
            await self.initialize()

        print("🔐 Authentification CAIJ...")

        try:
            # Naviguer vers page de connexion
            await self.page.goto("https://app.caij.qc.ca", timeout=30000)
            await self.page.wait_for_load_state("networkidle")

            # Étape 1: Email
            email_input = await self.page.wait_for_selector("#identifier", timeout=10000)
            await email_input.fill(self.credentials.email)

            continue_button = await self.page.wait_for_selector("button:has-text('Continuer')", timeout=5000)
            await continue_button.click()
            await self.page.wait_for_timeout(2000)

            # Étape 2: Mot de passe
            password_input = await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            await password_input.fill(self.credentials.password)
            await password_input.press("Enter")

            # Attendre navigation
            await self.page.wait_for_url(
                lambda url: "connexion" not in url.lower() and "login" not in url.lower(),
                timeout=15000
            )
            await self.page.wait_for_load_state("networkidle", timeout=15000)

            # Fermer popup CGU si présent
            try:
                close_button = await self.page.wait_for_selector('button[class*="close"]', timeout=3000)
                await close_button.click()
                await self.page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass  # Pas de popup

            self.authenticated = True
            print("✅ Authentification réussie")

        except Exception as e:
            print(f"❌ Échec authentification: {e}")
            # Screenshot d'erreur
            if self.page:
                await self.page.screenshot(path="caij_auth_error.png")
            raise

    async def search(self, request: CAIJSearchRequest) -> CAIJSearchResponse:
        """
        Effectuer une recherche sur CAIJ.

        Args:
            request: Requête de recherche

        Returns:
            Réponse avec résultats
        """
        start_time = time.time()

        # S'assurer d'être authentifié
        if not self.authenticated:
            await self.authenticate()

        # Rate limiting
        await self.rate_limiter.wait_if_needed()

        print(f"🔎 Recherche CAIJ: '{request.query}' (max {request.max_results} résultats)")

        try:
            # Toujours retourner à la page d'accueil pour réinitialiser le champ de recherche
            # Cela évite les problèmes lors de recherches multiples
            await self.page.goto("https://app.caij.qc.ca/fr", timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=20000)
            await self.page.wait_for_timeout(1500)

            # Fermer popup si présent
            try:
                close_button = await self.page.wait_for_selector('button[class*="close"]', timeout=2000)
                await close_button.click()
                await self.page.wait_for_timeout(500)
            except:
                pass

            # Chercher le champ de recherche (timeout augmenté pour recherches multiples)
            search_input = self.page.get_by_placeholder("Rechercher dans tout le contenu")
            await search_input.wait_for(timeout=20000)

            # Remplir et soumettre
            await search_input.fill(request.query)
            await search_input.press("Enter")

            # Attendre les résultats (timeout augmenté pour recherches multiples)
            await self.page.wait_for_timeout(3000)
            await self.page.wait_for_selector('div[class*="result"]', timeout=20000)

            # Extraire les résultats
            results = await self._extract_results(request.max_results)

            execution_time = time.time() - start_time

            response = CAIJSearchResponse(
                query=request.query,
                results=results,
                total_found=len(results),
                timestamp=datetime.now(),
                execution_time_seconds=round(execution_time, 2)
            )

            print(f"✅ {len(results)} résultats extraits en {execution_time:.2f}s")

            return response

        except Exception as e:
            print(f"❌ Erreur lors de la recherche: {e}")
            # Screenshot d'erreur
            if self.page:
                await self.page.screenshot(path="caij_search_error.png")
            raise

    async def _extract_results(self, max_results: int) -> List[CAIJResult]:
        """
        Extraire les résultats de recherche de la page actuelle.

        Args:
            max_results: Nombre maximum de résultats à extraire

        Returns:
            Liste des résultats
        """
        result_elements = await self.page.query_selector_all('div[class*="result"]')

        results = []
        for i, element in enumerate(result_elements[:max_results]):
            try:
                # Titre
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

                # Type de document
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

                # Extrait
                excerpt = "N/A"
                excerpt_el = await element.query_selector('.section-excerpt, .excerpt')
                if excerpt_el:
                    excerpt_text = await excerpt_el.text_content()
                    excerpt = excerpt_text.strip()[:500]  # Limiter à 500 chars

                # Nettoyer les données
                clean_title = title.strip() if title != "N/A" else "N/A"
                clean_url = url if url else "N/A"
                clean_doc_type = doc_type.strip() if doc_type != "N/A" else "N/A"
                clean_source = source.strip() if source != "N/A" else "N/A"
                clean_date = date.strip() if date != "N/A" else "N/A"

                # Déduire la rubrique
                rubrique = infer_rubrique(
                    document_type=clean_doc_type,
                    source=clean_source,
                    url=clean_url
                )

                # Créer le résultat
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
                print(f"  ⚠️  Erreur extraction résultat #{i+1}: {e}")
                continue

        return results

    async def __aenter__(self):
        """Support du context manager asynchrone."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fermer automatiquement à la sortie du context manager."""
        await self.close()
