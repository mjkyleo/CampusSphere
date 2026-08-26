"""Screenshots the CampusSphere frontend after our CSS / favicon fixes.

Verifies that:
1. Tailwind CSS injected classes actually take effect (look for a styled body background)
2. favicon.ico no longer 404s (the inline <link rel=icon> is present)
3. /api/users/me still 401s (because the dev session has no token) but
   we should see no other red errors after a short wait
"""
from playwright.sync_api import sync_playwright
import json
import os
import sys

URL = os.environ.get("URL", "http://localhost:5173/")
OUT_DIR = r"C:/Users/86132/.workbuddy/clipboard-images"
os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "campussphere-after-fix.png")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()

    requests_failed = []
    console_errors = []

    page.on("requestfailed", lambda req: requests_failed.append(f"{req.method} {req.url} -> {req.failure}"))
    page.on("response", lambda res: requests_failed.append(f"{res.status} {res.url}") if res.status >= 400 else None)
    page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))
    page.on("console", lambda msg: console_errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None)

    page.goto(URL, wait_until="domcontentloaded", timeout=15000)
    # give SPA a moment to render
    page.wait_for_timeout(2500)

    # Inspect rendered DOM state
    page_text = page.evaluate("() => document.body.innerText")[:1500]
    body_bg = page.evaluate("() => window.getComputedStyle(document.body).backgroundColor")
    nav_present = page.evaluate("""() => {
        const nav = document.querySelector('nav');
        if (!nav) return null;
        const s = window.getComputedStyle(nav);
        return {
          display: s.display,
          position: s.position,
          classes: nav.className,
        };
    }""")
    icon_svgs = page.evaluate("() => document.querySelectorAll('nav svg').length")
    inline_icon = page.evaluate("() => Array.from(document.querySelectorAll('link[rel*=icon]')).map(l => l.href.slice(0, 80))")
    head_styles = page.evaluate("() => Array.from(document.querySelectorAll('style')).map(s => s.textContent.length).reduce((a,b)=>a+b, 0)")

    page.screenshot(path=out_path, full_page=False)
    browser.close()

print("===STATE===")
print(json.dumps({
    "url": URL,
    "out_path": out_path,
    "body_bg": body_bg,
    "nav": nav_present,
    "icon_svgs_count": icon_svgs,
    "inline_icon_hrefs": inline_icon,
    "head_inline_style_chars": head_styles,
    "failed_requests": requests_failed,
    "console_errors": console_errors,
    "page_text_first": page_text,
}, ensure_ascii=False, indent=2))
