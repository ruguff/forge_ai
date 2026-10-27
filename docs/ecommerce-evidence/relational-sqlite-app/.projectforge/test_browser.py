import json
import subprocess
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

def wait_ready(url):
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=1).close()
            return
        except Exception:
            time.sleep(0.25)
    raise AssertionError("Preview server did not become ready: " + url)

def test_browser_journeys():
    journeys = json.loads(Path(__file__).with_name("browser.json").read_text())
    assert journeys, "No browser journeys defined"
    backend = subprocess.Popen(["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frontend = subprocess.Popen(["/opt/frontend/node_modules/.bin/vite", "--host", "127.0.0.1", "--port", "3001"], cwd="frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready("http://127.0.0.1:3001")
        wait_ready("http://127.0.0.1:8001/openapi.json")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for journey in journeys:
                    page = browser.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("pageerror", lambda error: print("Browser runtime error:", str(error), flush=True))
                    page.on("console", lambda message: print("Browser console:", message.text, flush=True) if message.type == "error" else None)
                    page.on("requestfailed", lambda request: print("Browser request failed:", request.url, request.failure, flush=True))
                    page.goto("http://127.0.0.1:3001")
                    for step in journey["steps"]:
                        action = step["action"]
                        if action == "goto":
                            path = step["path"]
                            assert path.startswith("/") and not path.startswith("//")
                            page.goto("http://127.0.0.1:3001" + path)
                        elif action == "fill":
                            page.locator(step["selector"]).fill(step["value"])
                        elif action == "click":
                            page.locator(step["selector"]).click()
                        elif action == "visible":
                            expect(page.locator(step["selector"])).to_be_visible()
                        elif action == "hidden":
                            expect(page.locator(step["selector"])).not_to_be_visible()
                        elif action == "text":
                            expect(page.locator(step["selector"])).to_contain_text(step["value"])
                        else:
                            raise AssertionError("Unsupported browser action")
                    assert not errors, errors
                    page.close()
            finally:
                browser.close()
    finally:
        frontend.terminate()
        backend.terminate()
        frontend.wait(timeout=5)
        backend.wait(timeout=5)
