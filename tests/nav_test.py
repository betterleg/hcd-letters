"""
Click-through test for the website's tabs (TODO #17). Fails if clicking a tab, or Back/Forward, doesn't show it.

    pip install playwright && python -m playwright install --with-deps chromium
    python3 scripts/build_site_data.py && python3 tests/nav_test.py site

Serves the site folder locally, opens each tab, leaves it, comes back, and uses Back and Forward,
on a desktop-sized and a phone-sized window. Exit code 1 on any failure.
"""
import asyncio
import subprocess
import sys
import time

from playwright.async_api import async_playwright

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
PORT = 8765
TABS = ["overview", "search", "requirements", "language", "trends", "statutes", "compliance", "place"]


async def run():
    failures, errors = [], []
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "-d", SITE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            for name, size in (("desktop", {"width": 1280, "height": 900}), ("phone", {"width": 390, "height": 800})):
                page = await browser.new_page(viewport=size)
                page.on("pageerror", lambda e, n=name: errors.append(f"{n}: {e}"))
                await page.goto(f"http://localhost:{PORT}/#overview")
                await page.wait_for_function("document.getElementById('stamp').textContent !== 'Loading…'", timeout=30000)

                async def showing():
                    return await page.evaluate("[...document.querySelectorAll('.panel')].find(p => !p.hidden)?.id")

                async def check(expect, what):
                    await page.wait_for_timeout(400)
                    got = await showing()
                    if got != expect:
                        failures.append(f"{name}: {what}: expected {expect}, showing {got} ({await page.evaluate('location.hash')})")

                async def click(tab):
                    await page.evaluate(f"document.querySelector('.tabs a[data-tab={tab}]').click()")

                # every tab, then back to search after each one
                for t in TABS:
                    await click(t)
                    await check(t, f"click {t}")
                    await click("search")
                    await check("search", f"click search after {t}")
                # a search survives leaving and coming back
                await page.fill("#sr-q", "parking")
                await page.evaluate("document.querySelector('#sr-form').requestSubmit()")
                await page.wait_for_timeout(1500)
                await click("trends")
                await check("trends", "click trends after a search")
                await click("search")
                await check("search", "click search again")
                if (await page.input_value("#sr-q")) != "parking":
                    failures.append(f"{name}: search words lost after leaving and coming back")
                # Back and Forward
                await click("compliance")
                await check("compliance", "click compliance")
                await page.go_back()
                await check("search", "Back from compliance")
                await page.go_forward()
                await check("compliance", "Forward to compliance")
                await page.close()
            await browser.close()
    finally:
        srv.terminate()
    for e in errors:
        print("PAGE ERROR", e)
    for f in failures:
        print("FAIL", f)
    print(f"{'FAILED' if failures or errors else 'OK'}: tab navigation ({len(failures)} failures, {len(errors)} page errors)")
    return 1 if failures or errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
