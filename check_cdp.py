import json
import urllib.request

# Get CDP WebSocket URL
ws_url = "ws://localhost:9222/devtools/browser/4fe30291-bb3b-4128-ac97-def29021ce71"

# Try to get console messages via Chrome DevTools Protocol
# First, let's list all pages
req = urllib.request.Request("http://localhost:9222/json/list")
try:
    with urllib.request.urlopen(req, timeout=5) as response:
        pages = json.loads(response.read())
        print(f"Found {len(pages)} pages/targets:")
        for page in pages:
            print(f"  - {page.get('title', 'No title')} ({page.get('url', 'No URL')})")
            if 'webSocketDebuggerUrl' in page:
                print(f"    WebSocket: {page['webSocketDebuggerUrl']}")
except Exception as e:
    print(f"Failed to list pages: {e}")
