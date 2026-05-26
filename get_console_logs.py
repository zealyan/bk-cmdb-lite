import json
import websocket
import threading
import time

# WebSocket URL for the details page
ws_url = "ws://localhost:9222/devtools/page/18C46F4EA317BEE8702C6E70BA10C4CF"

console_logs = []
lock = threading.Lock()

def on_message(ws, message):
    try:
        data = json.loads(message)
        # Check if it's a console message
        if data.get("method") == "Runtime.consoleAPICalled":
            params = data.get("params", {})
            msg_type = params.get("type", "log")
            args = params.get("args", [])
            
            # Extract text from args
            text_parts = []
            for arg in args:
                if arg.get("type") == "string":
                    text_parts.append(arg.get("value", ""))
                elif arg.get("type") == "number":
                    text_parts.append(str(arg.get("value", "")))
                elif arg.get("type") == "object":
                    # Try to get preview
                    preview = arg.get("preview", {})
                    if preview:
                        text_parts.append(json.dumps(preview))
                    else:
                        text_parts.append(arg.get("description", "{}"))
            
            text = " ".join(text_parts)
            console_logs.append({"type": msg_type, "text": text})
            print(f"[{msg_type}] {text[:300]}")
    except Exception as e:
        print(f"Error parsing message: {e}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket opened")
    # Enable console events
    ws.send(json.dumps({
        "id": 1,
        "method": "Runtime.enable"
    }))
    # Navigate to the details page
    ws.send(json.dumps({
        "id": 2,
        "method": "Page.navigate",
        "params": {"url": "http://localhost:8080/#/resource/instance/bk_slb_listener/1"}
    }))

# Create WebSocket connection
ws = websocket.WebSocketApp(
    ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
    on_open=on_open
)

# Run in a separate thread
ws_thread = threading.Thread(target=ws.run_forever)
ws_thread.daemon = True
ws_thread.start()

# Wait for messages
print("Waiting for console logs...")
time.sleep(10)

# Print summary
print(f"\n=== Summary ===")
print(f"Captured {len(console_logs)} console logs")
for log in console_logs:
    if 'instanceData' in log['text'] or 'DEBUG' in log['text'] or 'WATCH' in log['text']:
        print(f"[{log['type']}] {log['text'][:500]}")

# Close WebSocket
ws.close()
