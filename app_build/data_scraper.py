# =============================================================================
# "The Daily Audit" - Asset Scraping & Wikipedia Image Downloader Module
# =============================================================================
import os
import time
import requests
import urllib.parse
from PIL import Image
from io import BytesIO
from typing import Optional, Tuple

class DataScraper:
    """Handles programmatic scraping of public assets from Wikipedia and Wikimedia Commons."""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            # Default to an absolute path relative to this file, not CWD
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.cache_dir = os.path.join(base_dir, "assets", "scraped")
        else:
            self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.headers = {
            "User-Agent": "TheDailyAuditBot/1.0 (contact@thedailyaudit.internal)"
        }

    # Blocklist: Wikipedia page titles/categories to avoid (politics, gore, sensitive topics)
    CONTENT_BLOCKLIST = [
        "politic", "election", "president", "party", "democrat", "republican",
        "war", "battle", "weapon", "military", "conflict", "invasion",
        "murder", "kill", "death", "violence", "abuse", "torture",
        "terror", "bomb", "explosion", "massacre", "genocide",
        "porn", "nude", "sexual", "explicit", "adult",
        "gun", "shooting", "assault", "attack",
        "racism", "nazi", "holocaust", "slavery",
        "drug", "overdose", "suicide", "self-harm",
    ]

    def _is_content_safe(self, page_title: str) -> Tuple[bool, str]:
        """Check if a Wikipedia page is safe for a teen+ audience.
        Returns (is_safe, reason) tuple.
        Skips pages whose titles contain blocked keywords."""
        title_lower = page_title.lower()
        for keyword in self.CONTENT_BLOCKLIST:
            if keyword in title_lower:
                return False, f"title contains blocked keyword '{keyword}'"
        # Also check page categories via API for deeper filtering
        try:
            cat_url = (
                "https://en.wikipedia.org/w/api.php?"
                "action=query&format=json&prop=categories&"
                f"titles={urllib.parse.quote(page_title)}&formatversion=2"
            )
            r_cat = requests.get(cat_url, headers=self.headers, timeout=8)
            if r_cat.status_code == 200:
                pages_data = r_cat.json().get("query", {}).get("pages", [])
                if pages_data and "categories" in pages_data[0]:
                    for cat in pages_data[0]["categories"]:
                        cat_title = cat.get("title", "").lower()
                        for keyword in self.CONTENT_BLOCKLIST:
                            if keyword in cat_title:
                                return False, f"category '{cat_title}' contains blocked keyword '{keyword}'"
        except Exception:
            pass  # non-blocking — category check is best-effort
        return True, ""

    def fetch_wikipedia_image(self, query: str, filename_prefix: str) -> Optional[str]:
        """
        Queries Wikipedia's API for the best matching article, retrieves its primary
        page image (thumbnail), downloads it, and saves it locally.
        
        Returns the absolute local file path of the downloaded image, or None if failed.
        """
        if not query or not query.strip():
            print("[Scraper] Empty query provided. Skipping search.")
            return None

        clean_query = query.strip()
        print(f"[Scraper] Querying Wikipedia for: '{clean_query}'")

        # Step 1: Perform search to find the best matching Wikipedia article title
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            "action=query&format=json&list=search&"
            f"srsearch={urllib.parse.quote(clean_query)}&utf8=1&formatversion=2"
        )

        try:
            r = requests.get(search_url, headers=self.headers, timeout=10)
            r.raise_for_status()
            search_results = r.json().get("query", {}).get("search", [])
            if not search_results:
                print(f"[Scraper] No search results found for: '{clean_query}'")
                return None

            # Find first search result that passes content safety check
            best_match_title = None
            for result in search_results:
                candidate = result["title"]
                is_safe, reason = self._is_content_safe(candidate)
                if is_safe:
                    best_match_title = candidate
                    print(f"[Scraper] Best safe matching page: '{best_match_title}'")
                    break
                else:
                    print(f"[Scraper] Skipping '{candidate}' — {reason}")

            if not best_match_title:
                print(f"[Scraper] All search results for '{clean_query}' blocked by content filter.")
                return None

            # Step 2: Query page info to retrieve its main thumbnail image (800px size)
            image_url_query = (
                "https://en.wikipedia.org/w/api.php?"
                "action=query&format=json&prop=pageimages&"
                f"titles={urllib.parse.quote(best_match_title)}&"
                "pithumbsize=800&formatversion=2"
            )

            r_img = requests.get(image_url_query, headers=self.headers, timeout=10)
            r_img.raise_for_status()
            pages = r_img.json().get("query", {}).get("pages", [])
            if not pages or "thumbnail" not in pages[0]:
                print(f"[Scraper] Wikipedia page '{best_match_title}' has no primary thumbnail image.")
                return None

            img_download_url = pages[0]["thumbnail"]["source"]
            print(f"[Scraper] Downloading page image: {img_download_url}")

            # Step 3: Fetch the image bytes and save it locally
            r_data = requests.get(img_download_url, headers=self.headers, timeout=15)
            r_data.raise_for_status()
            
            # Verify and open the image via Pillow
            image = Image.open(BytesIO(r_data.content)).convert("RGB")
            
            # Define output path with unique timestamp to prevent filename collisions
            safe_prefix = "".join(c for c in filename_prefix if c.isalnum() or c in ("-", "_")).rstrip()
            out_filename = f"{safe_prefix}_{int(time.time() * 1000)}.png"
            out_path = os.path.join(self.cache_dir, out_filename)
            
            # Save the image
            image.save(out_path, "PNG")
            print(f"[Scraper] Image successfully saved to: {out_path}")
            return os.path.abspath(out_path)

        except Exception as e:
            print(f"[Scraper] Failed to fetch Wikipedia image for '{clean_query}': {e}")
            return None

    def fetch_multiple_wikipedia_images(self, queries: list, filename_prefix: str, max_images: int = 3) -> list:
        """
        Fetches up to max_images Wikipedia images from a list of queries.
        Returns paths for successfully downloaded images (1 to max_images).
        """
        paths = []
        for idx, query in enumerate(queries):
            if len(paths) >= max_images:
                break
            if not query or not query.strip():
                continue
            fname = f"{filename_prefix}_scene{idx}"
            try:
                path = self.fetch_wikipedia_image(query, fname)
                if path:
                    paths.append(os.path.abspath(path))
                    print(f"[Scraper] Scene {idx} image fetched: {path}")
            except Exception as e:
                print(f"[Scraper] Scene {idx} fetch failed for '{query}': {e}")
        print(f"[Scraper] Total images fetched: {len(paths)} (target: 1-{max_images})")
        return paths

    def fetch_google_image(self, query: str, filename_prefix: str) -> Optional[str]:
        """
        Searches Google Images for the query and downloads the first result.
        Intended as a fallback when Wikipedia has no relevant image.
        Uses web scraping of publicly accessible Google Image search results (fair use for thumbnails).
        """
        if not query or not query.strip():
            print("[Scraper] Empty Google image query. Skipping.")
            return None

        clean_query = query.strip()
        print(f"[Scraper] Querying Google Images for: '{clean_query}'")

        google_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            search_url = (
                "https://www.google.com/search?"
                f"q={urllib.parse.quote(clean_query)}&tbm=isch&safe=active"
            )
            r = requests.get(search_url, headers=google_headers, timeout=15)
            r.raise_for_status()

            import re
            urls = []
            for pattern in [
                r'"(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                r'"(https://[^"]+googleusercontent[^"]+)"',
                r'"(https://[^"]+wikimedia[^"]+)"',
                r'"(https://[^"]+static[^"]+\.(?:jpg|jpeg|png))"',
                r'"(https://[^"]+images[^"]+\.(?:jpg|jpeg|png))"',
            ]:
                found = re.findall(pattern, r.text, re.IGNORECASE)
                for u in found:
                    u_clean = u.replace("\\u003d", "=").replace("\\u0026", "&")
                    if u_clean not in urls and any(ext in u_clean.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        urls.append(u_clean)

            if not urls:
                print(f"[Scraper] No image URLs found in Google Images for '{clean_query}'")
                return None

            for img_url in urls[:5]:
                try:
                    r_img = requests.get(img_url, headers=google_headers, timeout=15)
                    r_img.raise_for_status()
                    image = Image.open(BytesIO(r_img.content)).convert("RGB")
                    safe_prefix = "".join(c for c in filename_prefix if c.isalnum() or c in ("-", "_")).rstrip()
                    out_filename = f"{safe_prefix}_google_{int(time.time() * 1000)}.png"
                    out_path = os.path.join(self.cache_dir, out_filename)
                    image.save(out_path, "PNG")
                    print(f"[Scraper] Google Image saved: {out_path}")
                    return os.path.abspath(out_path)
                except Exception as e:
                    print(f"[Scraper] Failed to download Google image URL {img_url[:60]}: {e}")
                    continue

            return None

        except Exception as e:
            print(f"[Scraper] Google Images search failed for '{clean_query}': {e}")
            return None

    def fetch_image_multi_source(self, query: str, filename_prefix: str) -> Optional[str]:
        """
        Tries multiple sources in order: Wikipedia -> Google Images -> None.
        Returns the path of the first successfully downloaded image.
        """
        path = self.fetch_wikipedia_image(query, filename_prefix)
        if path:
            return path
        print(f"[Scraper] Wikipedia failed for '{query}', trying Google Images...")
        path = self.fetch_google_image(query, filename_prefix)
        return path

    def fetch_scene_images(self, queries: list, filename_prefix: str, max_images: int = 3) -> list:
        """
        Fetches up to max_images from multiple sources (Wikipedia then Google).
        Each query uses fetch_image_multi_source for maximum coverage.
        Returns 1 to max_images image paths.
        """
        paths = []
        for idx, query in enumerate(queries):
            if len(paths) >= max_images:
                break
            if not query or not query.strip():
                continue
            fname = f"{filename_prefix}_scene{idx}"
            path = self.fetch_image_multi_source(query, fname)
            if path:
                paths.append(path)
                print(f"[Scraper] Scene {idx} image secured: {path}")
        print(f"[Scraper] Total scene images: {len(paths)} (target: 1-{max_images})")
        return paths

    def scrape_wikipedia_summary(self, query: str) -> str:
        """
        Retrieves the plain-text intro section of the Wikipedia article matching the query.
        """
        if not query or not query.strip():
            return ""
        clean_query = query.strip()
        
        # Step 1: Search Wikipedia
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            "action=query&format=json&list=search&"
            f"srsearch={urllib.parse.quote(clean_query)}&utf8=1&formatversion=2"
        )
        try:
            r = requests.get(search_url, headers=self.headers, timeout=10)
            r.raise_for_status()
            search_results = r.json().get("query", {}).get("search", [])
            if not search_results:
                return f"No direct search results found for topic: {clean_query}"
            
            best_match_title = search_results[0]["title"]
            snippet = search_results[0].get("snippet", "")
            
            # Step 2: Get intro extract
            extract_url = (
                "https://en.wikipedia.org/w/api.php?"
                "action=query&format=json&prop=extracts&exintro=1&explaintext=1&"
                f"titles={urllib.parse.quote(best_match_title)}&formatversion=2"
            )
            r_ext = requests.get(extract_url, headers=self.headers, timeout=10)
            r_ext.raise_for_status()
            pages = r_ext.json().get("query", {}).get("pages", [])
            if pages and "extract" in pages[0]:
                return pages[0]["extract"]
            
            import re
            clean_snippet = re.sub(r'<[^>]+>', '', snippet)
            return f"Topic: {best_match_title}. Summary: {clean_snippet}"
        except Exception as e:
            return f"Error searching research data for '{clean_query}': {e}"

