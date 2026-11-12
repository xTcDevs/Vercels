"""Smoke-test the Zaga static site: loads it, checks the filter and contact form, saves screenshots."""
import sys
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError, sync_playwright


def run(site_dir: Path, shots_dir: Path) -> int:
    index = site_dir / "index.html"
    if not index.is_file():
        print(f"Error: {index} not found", file=sys.stderr)
        return 1
    try:
        shots_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: cannot create {shots_dir}: {e}", file=sys.stderr)
        return 1
    url = index.resolve().as_uri()
    page_errors, failures = [], []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for width, name in [(1440, "desktop"), (390, "phone")]:
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page.on("pageerror", lambda e: page_errors.append(str(e)))
                    page.goto(url, timeout=15000)
                    page.wait_for_timeout(400)
                    page.screenshot(path=str(shots_dir / f"{name}.png"))
                    page.locator("#collection").scroll_into_view_if_needed()
                    page.evaluate("window.scrollTo(0, document.getElementById('shop-tabs').getBoundingClientRect().top + window.scrollY - 90)")
                    page.wait_for_timeout(600)
                    page.screenshot(path=str(shots_dir / f"{name}-shop.png"))

                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(url, timeout=15000)
                if page.locator(".card").count() != 14:
                    failures.append(f"shop: expected 14 cards, got {page.locator('.card').count()}")
                page.click('#shop-tabs button[data-cat="Hoodies"]')
                if page.locator(".card").count() != 3:
                    failures.append(f"filter: expected 3 hoodies, got {page.locator('.card').count()}")
                first = page.locator(".card").first
                first.locator('.swatch[data-key="navy"]').click()
                if "-navy.webp" not in (first.locator("img").get_attribute("src") or ""):
                    failures.append("swatch: card image did not switch to navy")
                first.locator(".card-cta").click()
                if not page.locator("#quick-view").is_visible():
                    failures.append("quick view did not open")
                page.click('#qv-swatches .swatch[data-key="burgundy"]')
                if "-burgundy.webp" not in (page.locator("#qv-img").get_attribute("src") or ""):
                    failures.append("quick view swatch did not switch image")
                page.click('#qv-sizes .size[data-size="L"]')
                page.wait_for_timeout(300)
                page.screenshot(path=str(shots_dir / "quick-view.png"))
                page.click("#qv-order")
                details = page.locator('#contact-form textarea[name="details"]').input_value()
                if "Burgundy" not in details or "size L" not in details:
                    failures.append(f"order did not reach contact form: {details!r}")
                page.click('#shop-tabs button[data-cat="All"]')
                page.screenshot(path=str(shots_dir / "after-order.png"))
                page.fill("input[name=name]", "Test")
                page.fill("input[name=phone]", "08000000000")
                page.click("#contact-form button[type=submit]")
                if not page.locator("#contact-sent").is_visible():
                    failures.append("contact form: success message not shown")
            finally:
                browser.close()
    except (PlaywrightError, OSError) as e:
        print(f"Error: browser test failed: {e}", file=sys.stderr)
        return 1

    for err in page_errors:
        failures.append(f"JS error: {err}")
    if failures:
        print("FAILED:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print(f"All checks passed. Screenshots in {shots_dir.resolve()}")
    return 0


if __name__ == "__main__":
    site = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    shots = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tools/screenshots")
    sys.exit(run(site, shots))
