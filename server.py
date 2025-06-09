from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import socket
import uvicorn
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Serve frontend files from the camera-scanner directory
frontend_dir = Path(__file__).resolve().parent / "camera-scanner"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

SAVE_DIR = Path(__file__).resolve().parent / "camera-scanner" / "backend" / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

@app.post("/save-image")
async def save_image(req: Request):
    data = await req.json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    filename = SAVE_DIR / f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    with open(filename, 'wb') as f:
        f.write(img_bytes)
    return {"status": "saved", "file": str(filename)}

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000

    print("=" * 60)
    print("\U0001F4F1 DOCUMENT SCANNER SERVER STARTING")
    print("=" * 60)
    print(f"\U0001F5A5\FE0F  Local access: http://localhost:{port}")
    print(f"\U0001F4F1 Phone access: http://{local_ip}:{port}")
    print("=" * 60)
    print("\U0001F4CB Instructions:")
    print("1. Make sure your phone is on the same WiFi network")
    print("2. Open the phone URL in your mobile browser")
    print("3. Allow camera permissions when prompted")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=port)
