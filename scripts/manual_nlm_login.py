"""
Manual NotebookLM Login - Bypass Win11 cookie extraction issue (#181)
"""
import json
import subprocess
import time
import os
import re
from pathlib import Path

NLM_PROFILE_DIR = Path.home() / ".notebooklm-mcp-cli" / "profiles" / "default"
CHROME_PROFILE_DIR = Path.home() / ".notebooklm-mcp-cli" / "chrome-profiles" / "default"
PORT = 9234
NOTEBOOKLM_URL = "https://notebooklm.google.com"

CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

chrome_paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]
chrome_path = None
for p in chrome_paths:
    if os.path.exists(p):
        chrome_path = p
        break

if not chrome_path:
    print("[ERROR] Chrome not found")
    exit(1)

print(f"[OK] Chrome: {chrome_path}")

args = [
    chrome_path,
    f"--remote-debugging-port={PORT}",
    "--no-first-run",
    "--no-default-browser-check",
    f"--user-data-dir={CHROME_PROFILE_DIR}",
    f"--remote-allow-origins=http://127.0.0.1:{PORT}",
    NOTEBOOKLM_URL,
]

print(f"[INFO] Starting Chrome (port {PORT})...")
print(f"[INFO] Profile: {CHROME_PROFILE_DIR}")
print("=" * 60)
print("STEPS:")
print("1. In the Chrome window, sign into your Google account")
print("2. Then navigate to: notebooklm.google.com")
print("3. Wait for NotebookLM to fully load")
print("4. Keep the window open, script waits up to 120s")
print("=" * 60)

process = subprocess.Popen(
    args,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)

import httpx
import websocket

start = time.time()
print("[WAIT] Chrome CDP starting...")

while time.time() - start < 30:
    try:
        r = httpx.get(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
        if r.status_code == 200:
            ws_url = r.json().get("webSocketDebuggerUrl", "")
            if ws_url:
                ws_url = ws_url.replace("://localhost:", "://127.0.0.1:")
                print(f"[OK] CDP ready on port {PORT}")
                break
    except Exception:
        pass
    time.sleep(1)
else:
    print("[ERROR] CDP not ready after 30s")
    process.terminate()
    exit(1)

print("\n[WAIT] Waiting for NotebookLM page to fully load (max 120s)...")
print("  -> Please sign in and navigate to notebooklm.google.com")

notebooklm_ready = False
cookies_extracted = False

while time.time() - start < 120:
    elapsed = int(time.time() - start)
    try:
        pages = httpx.get(f"http://127.0.0.1:{PORT}/json", timeout=3).json()
        for page in pages:
            url = page.get("url", "")
            ws = page.get("webSocketDebuggerUrl", "")

            if "notebooklm.google.com" in url and ws:
                ws = ws.replace("://localhost:", "://127.0.0.1:")

                if not notebooklm_ready:
                    print(f"\n[OK] Detected NotebookLM page ({elapsed}s)")
                    print("[WAIT] Waiting 60s for full page load and session cookies...")
                    for i in range(60):
                        if i % 10 == 0 and i > 0:
                            print(f"  Still loading... ({i}s)")
                        time.sleep(1)
                    notebooklm_ready = True

                # Extract cookies via CDP
                ws_conn = websocket.create_connection(ws, timeout=10, suppress_origin=True)
                ws_conn.send(json.dumps({"id": 1, "method": "Network.getAllCookies", "params": {}}))
                ws_conn.settimeout(10)

                while True:
                    response = json.loads(ws_conn.recv())
                    if response.get("id") == 1:
                        cookies = response.get("result", {}).get("cookies", [])
                        ws_conn.close()

                        if len(cookies) > 0:
                            # Get page HTML for CSRF token and build label
                            ws_conn2 = websocket.create_connection(ws, timeout=10, suppress_origin=True)
                            ws_conn2.send(json.dumps({"id": 1, "method": "Runtime.enable", "params": {}}))
                            time.sleep(0.5)
                            ws_conn2.send(json.dumps({
                                "id": 2, "method": "Runtime.evaluate",
                                "params": {"expression": "document.documentElement.outerHTML"}
                            }))
                            ws_conn2.settimeout(10)

                            html = ""
                            while True:
                                resp = json.loads(ws_conn2.recv())
                                if resp.get("id") == 2:
                                    html = resp.get("result", {}).get("result", {}).get("value", "")
                                    break
                            ws_conn2.close()

                            csrf_match = re.search(r'"SNlM0e":"([^"]+)"', html)
                            csrf = csrf_match.group(1) if csrf_match else ""

                            bl_match = re.search(r'"cfb2h":"([^"]+)"', html)
                            build_label = bl_match.group(1) if bl_match else ""

                            nlm_cookies = [c for c in cookies if "notebooklm" in c.get("domain", "")]
                            google_cookies = [c for c in cookies if "google.com" in c.get("domain", "") and "notebooklm" not in c.get("domain", "")]

                            print(f"\n[Cookie Stats]")
                            print(f"  Total: {len(cookies)}")
                            print(f"  notebooklm.google.com domain: {len(nlm_cookies)}")
                            print(f"  .google.com domain: {len(google_cookies)}")
                            for c in nlm_cookies:
                                print(f"    - {c['name']} ({c['domain']})")
                            print(f"  CSRF Token: {'YES' if csrf else 'NO'}")
                            print(f"  Build Label: {'YES' if build_label else 'NO'}")

                            # Save to nlm profile
                            NLM_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
                            with open(NLM_PROFILE_DIR / "cookies.json", "w", encoding="utf-8") as f:
                                json.dump(cookies, f, indent=2)
                            print(f"\n[OK] Saved {len(cookies)} cookies")

                            from datetime import datetime
                            metadata = {
                                "csrf_token": csrf,
                                "session_id": "",
                                "email": "clementsorlanda965@gmail.com",
                                "build_label": build_label,
                                "last_validated": datetime.now().isoformat(),
                            }
                            with open(NLM_PROFILE_DIR / "metadata.json", "w", encoding="utf-8") as f:
                                json.dump(metadata, f, indent=2)
                            print("[OK] Metadata saved")

                            cookies_extracted = True
                        break

                if cookies_extracted:
                    break

        if cookies_extracted:
            break

    except Exception:
        pass

    if elapsed % 10 == 0:
        print(f"  Waiting... ({elapsed}s)")
    time.sleep(2)

# Close Chrome
print("\n[INFO] Closing Chrome...")
try:
    ws_conn = websocket.create_connection(ws, timeout=5, suppress_origin=True)
    ws_conn.send(json.dumps({"id": 1, "method": "Browser.close", "params": {}}))
    ws_conn.close()
except Exception:
    process.terminate()

process.wait(timeout=10)

if cookies_extracted:
    print("\n[SUCCESS] Login successful! nlm is ready to use.")
else:
    print(f"\n[ERROR] Timed out before cookie extraction completed.")
    print("Please retry and make sure notebooklm.google.com loads fully.")
