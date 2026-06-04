from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import UploadFile
from pypdf import PdfReader

from inkdesk_server.security import ApiError


@dataclass(frozen=True)
class ImportedRawMaterial:
    kind: str
    title: str
    locator: str | None
    excerpt: str
    body: str


@dataclass(frozen=True)
class WebAssistResult:
    url: str
    title: str
    excerpt: str
    body: str
    reason_used: str


class WebRawImportService:
    search_url = "https://html.duckduckgo.com/html/"
    user_agent = "Inkdesk/1.0 (+https://inkdesk.local)"
    max_web_assist_results = 3

    def assist_from_query(self, query: str) -> list[WebAssistResult]:
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        results: list[WebAssistResult] = []
        seen_urls: set[str] = set()
        for raw_url, title in self._search_result_candidates(normalized_query):
            resolved_url = self._resolve_result_url(raw_url)
            if not resolved_url or resolved_url in seen_urls:
                continue
            seen_urls.add(resolved_url)
            try:
                material = self.import_from_url(resolved_url, title)
            except ApiError:
                continue
            results.append(
                WebAssistResult(
                    url=resolved_url,
                    title=material.title,
                    excerpt=material.excerpt,
                    body=material.body,
                    reason_used=f"它补足了问题“{normalized_query}”相关的 vault 外部证据。",
                )
            )
            if len(results) >= self.max_web_assist_results:
                break
        return results

    def import_from_url(self, url: str, title_override: str | None) -> ImportedRawMaterial:
        normalized_url = (url or "").strip()
        if not (normalized_url.startswith("http://") or normalized_url.startswith("https://")):
            raise ApiError(400, "BAD_REQUEST", "Web import requires an http or https URL.")

        try:
            response = self._fetch_url(normalized_url)
        except httpx.HTTPError as exc:
            raise ApiError(502, "BAD_GATEWAY", f"Unable to fetch webpage: {normalized_url}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        body = " ".join(soup.body.stripped_strings) if soup.body else " ".join(soup.stripped_strings)
        body = body.strip()
        if not body:
            raise ApiError(400, "BAD_REQUEST", "The fetched webpage did not contain readable text.")
        title = (title_override or "").strip() or soup.title.string.strip() if soup.title and soup.title.string else normalized_url
        excerpt = self._first_paragraph(soup, body)
        return ImportedRawMaterial("WEB", title, normalized_url, excerpt, body)

    def _first_paragraph(self, soup: BeautifulSoup, fallback: str) -> str:
        for element in soup.select("article p, main p, p"):
            text = element.get_text(" ", strip=True)
            if text:
                return text
        return self._first_sentence(fallback)

    def _first_sentence(self, value: str) -> str:
        text = value.strip()
        indexes = [index for index in (text.find("。"), text.find(".")) if index >= 0]
        return text[: min(indexes) + 1].strip() if indexes else text

    def _fetch_url(self, url: str) -> httpx.Response:
        response = httpx.get(
            url,
            headers={"User-Agent": self.user_agent},
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response

    def _search_result_candidates(self, query: str) -> list[tuple[str, str]]:
        try:
            response = httpx.get(
                self.search_url,
                params={"q": query},
                headers={"User-Agent": self.user_agent},
                timeout=15.0,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        candidates: list[tuple[str, str]] = []
        for link in soup.select("a.result__a, a.result-link, a[data-testid='result-title-a']"):
            href = (link.get("href") or "").strip()
            title = link.get_text(" ", strip=True)
            if href and title:
                candidates.append((href, title))
        return candidates

    def _resolve_result_url(self, raw_url: str) -> str | None:
        normalized = (raw_url or "").strip()
        if not normalized:
            return None
        if normalized.startswith("//"):
            normalized = f"https:{normalized}"
        parsed = urlparse(normalized)
        if parsed.netloc.endswith("duckduckgo.com"):
            target = parse_qs(parsed.query).get("uddg", [None])[0]
            if target:
                return unquote(target)
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        return None


class PdfRawImportService:
    def import_pdf(self, file: UploadFile, title_override: str | None, locator_override: str | None) -> ImportedRawMaterial:
        if file is None:
            raise ApiError(400, "BAD_REQUEST", "PDF import requires a file.")
        file_name = (file.filename or "upload.pdf").strip() or "upload.pdf"
        content = file.file.read()
        if not content:
            raise ApiError(400, "BAD_REQUEST", "PDF import requires a file.")
        try:
            reader = PdfReader(BytesIO(content))
            body = " ".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        except Exception as exc:
            raise ApiError(400, "BAD_REQUEST", "Unable to read the uploaded PDF.") from exc
        if not body:
            raise ApiError(400, "BAD_REQUEST", "The uploaded PDF did not contain extractable text.")
        title = (title_override or "").strip() or file_name.removesuffix(".pdf")
        locator = (locator_override or "").strip() or f"upload://{file_name}"
        return ImportedRawMaterial("PDF", title, locator, self._first_sentence(body), body)

    def _first_sentence(self, value: str) -> str:
        text = " ".join(value.split()).strip()
        indexes = [index for index in (text.find("。"), text.find(".")) if index >= 0]
        return text[: min(indexes) + 1].strip() if indexes else text
