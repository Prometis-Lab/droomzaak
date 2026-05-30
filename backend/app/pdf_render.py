"""Render the self-contained pakket HTML to PDF via headless Chromium (Playwright).

The pakket HTML is fully self-contained — inline CSS, no external assets/fonts/JS
(see templates/pakket.html) — so `set_content` needs no base URL and no network.
`page.pdf()` emulates print media by default, so the template's `@media print`
rules apply automatically: the action bar is hidden and colours are preserved.

Playwright is an optional capability: the import is lazy so the app boots (and the
browser-print fallback still works) even if Playwright/Chromium aren't installed.
Tests monkeypatch `html_to_pdf` — they never launch a real browser.
"""

from __future__ import annotations

_PDF_MARGIN = {"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"}


async def html_to_pdf(html: str) -> bytes:
    """Render a self-contained HTML string to A4 PDF bytes.

    Raises (ImportError / Playwright errors) if the engine or Chromium is missing;
    the caller turns that into a 503 so the browser-print fallback stays usable.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="load")
            return await page.pdf(format="A4", print_background=True, margin=_PDF_MARGIN)
        finally:
            await browser.close()
