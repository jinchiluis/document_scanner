from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import socket

app = FastAPI()

# Serve frontend files
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent, html=True), name="static")

SAVE_DIR = Path(__file__).resolve().parent / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/save-image")
async def save_image(req: Request):
    data = await req.json()
    img_data = data['image'].split(',')[1]
    img_bytes = base64.b64decode(img_data)
    filename = SAVE_DIR / f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    with open(filename, 'wb') as f:
        f.write(img_bytes)
    return {"status": "saved", "file": str(filename)}

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote server to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    
    print("=" * 50)
    print("📱 MOBILE DOCUMENT SCANNER READY!")
    print("=" * 50)
    print(f"🖥️  PC Access: http://127.0.0.1:{port}")
    print(f"📱 Phone Access: http://{local_ip}:{port}")
    print("=" * 50)
    print("📋 Instructions:")
    print("1. Make sure your phone and PC are on the same WiFi")
    print(f"2. Open your phone's browser (Chrome/Safari)")
    print(f"3. Go to: http://{local_ip}:{port}")
    print("4. Allow camera access when prompted")
    print("5. Start scanning documents!")
    print("=" * 50)
    
    # Run server accessible from network
    uvicorn.run(
        "server:app", 
        host="0.0.0.0",  # Allow connections from other devices
        port=port,
        reload=True
    )
