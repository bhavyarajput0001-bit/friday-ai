import re, json, urllib.parse, time
from pathlib import Path

BROWSER_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    BROWSER_AVAILABLE = True
except ImportError:
    pass

class WebAgent:
    def __init__(self):
        self._browser = None
        self._page = None
        self._playwright = None
        self.available = BROWSER_AVAILABLE

    def _ensure_browser(self):
        if not self.available:
            return False
        try:
            if self._browser is None:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(headless=True)
                self._page = self._browser.new_page()
            return True
        except Exception as e:
            print(f"[WebAgent] Browser error: {e}")
            self._cleanup()
            return False

    def _cleanup(self):
        try:
            if self._page:
                self._page.close()
        except: pass
        try:
            if self._browser:
                self._browser.close()
        except: pass
        try:
            if self._playwright:
                self._playwright.stop()
        except: pass
        self._page = None
        self._browser = None
        self._playwright = None

    def search_google(self, query, max_results=5):
        if not self._ensure_browser():
            return {"error": "Browser unavailable", "results": []}
        try:
            encoded = urllib.parse.quote(query)
            self._page.goto(f"https://www.google.com/search?q={encoded}", timeout=15000, wait_until="domcontentloaded")
            time.sleep(1.5)
            results = []
            items = self._page.query_selector_all("div.g")
            for item in items[:max_results]:
                try:
                    title_el = item.query_selector("h3")
                    link_el = item.query_selector("a")
                    if not title_el: continue
                    title = title_el.inner_text()
                    link = link_el.get_attribute("href") if link_el else ""
                    snippet_el = item.query_selector("div[data-sncf], span.aCOpRe, div.VwiC3b")
                    snippet = snippet_el.inner_text() if snippet_el else ""
                    if title:
                        results.append({"title": title, "link": link, "snippet": snippet})
                except: continue
            self._cleanup()
            return {"query": query, "results": results, "source": "google"}
        except Exception as e:
            self._cleanup()
            return {"error": str(e), "results": []}

    def search_youtube(self, query, max_results=3):
        if not self._ensure_browser():
            return {"error": "Browser unavailable", "results": []}
        try:
            encoded = urllib.parse.quote(query)
            self._page.goto(f"https://www.youtube.com/results?search_query={encoded}", timeout=15000, wait_until="domcontentloaded")
            time.sleep(2)
            results = []
            items = self._page.query_selector_all("ytd-video-renderer")
            for item in items[:max_results]:
                try:
                    title_el = item.query_selector("#video-title")
                    title = title_el.get_attribute("title") or title_el.inner_text()
                    link = "https://youtube.com" + (title_el.get_attribute("href") or "")
                    results.append({"title": title, "link": link})
                except: continue
            self._cleanup()
            return {"query": query, "results": results, "source": "youtube"}
        except Exception as e:
            self._cleanup()
            return {"error": str(e), "results": []}

    def read_page(self, url):
        if not self._ensure_browser():
            return {"error": "Browser unavailable"}
        try:
            self._page.goto(url, timeout=20000, wait_until="domcontentloaded")
            time.sleep(1)
            title = self._page.title()
            body = self._page.evaluate("document.body.innerText")
            text = body[:5000]
            self._cleanup()
            return {"url": url, "title": title, "content": text, "length": len(body)}
        except Exception as e:
            self._cleanup()
            return {"error": str(e)}

    def close(self):
        self._cleanup()

    def format_results_for_chat(self, results):
        if "error" in results:
            return f"⚠️ Web search error: {results['error']}"
        if not results.get("results"):
            return "🔍 No results found."
        lines = [f"🔍 Search results for: {results['query']}"]
        for r in results["results"][:5]:
            lines.append(f"\n**{r['title']}**")
            if r.get("snippet"):
                lines.append(f"> {r['snippet'][:200]}")
            if r.get("link"):
                lines.append(f"🔗 {r['link']}")
        return "\n".join(lines)
