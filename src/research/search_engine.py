import time
from typing import List, Dict, Any
from config.settings import MAX_SEARCH_RESULTS, REQUEST_TIMEOUT_SECONDS

class SearchEngine:
    def __init__(self):
        self._cache: Dict[str, List[Dict[str, str]]] = {}

    def search(self, query: str, max_results: int = MAX_SEARCH_RESULTS) -> List[Dict[str, str]]:
        """Searches DuckDuckGo for technical motorcycle specs and snippets."""
        clean_query = query.strip()
        if not clean_query:
            return []

        if clean_query in self._cache:
            return self._cache[clean_query]

        results = []
        try:
            from ddgs import DDGS
            with DDGS(timeout=REQUEST_TIMEOUT_SECONDS) as ddgs:
                ddg_gen = ddgs.text(
                    clean_query,
                    region="mx-es",
                    safesearch="moderate",
                    max_results=max_results,
                )
                for item in ddg_gen:
                    results.append({
                        "title": item.get("title", ""),
                        "body": item.get("body", item.get("snippet", "")),
                        "href": item.get("href", item.get("link", "")),
                    })
        except Exception as e:
            # Fallback using duckduckgo_search legacy or return empty gracefully
            try:
                from duckduckgo_search import DDGS as DDGSLegacy
                with DDGSLegacy(timeout=REQUEST_TIMEOUT_SECONDS) as ddgs:
                    ddg_gen = ddgs.text(clean_query, region="mx-es", max_results=max_results)
                    for item in ddg_gen:
                        results.append({
                            "title": item.get("title", ""),
                            "body": item.get("body", ""),
                            "href": item.get("href", ""),
                        })
            except Exception as e2:
                print(f"[SearchEngine] Warning: DuckDuckGo search failed for '{query}': {e2}")

        self._cache[clean_query] = results
        return results
