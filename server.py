from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import socket

app = FastAPI()

# Since server.py is in parent folder of camera-scanner
# Structure: 
# parent-folder/
# ├── server.py          ← YOU ARE HERE
# └── camera-scanner/
#     ├── index.html
#     ├── styles.css
#     └── script.js

# Path to camera-scanner folder
frontend_dir = Path(__file__).resolve().parent / "camera-scanner"
print(f"Looking for camera-scanner folder at: {frontend_dir}")

# Check if camera-scanner folder exists
if not frontend_dir.exists():
    print("ERROR: camera-scanner folder not found!")
    print("Current directory contents:")
    for item in Path(__file__).resolve().parent.iterdir():
        print(f"  📁 {item.name}")
else:
    print(f"✅ Found camera-scanner folder")
    print("Contents of camera-scanner folder:")
    for item in frontend_dir.iterdir():
        print(f"  📄 {item.name}")

# Create saved_docs folder next to server.py
SAVE_DIR = Path(__file__).resolve().parent / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
print(f"Documents will be saved to: {SAVE_DIR}")

# Mount static files from camera-scanner folder
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def serve_index():
    """Serve the main page"""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(
            content=f"<h1>Error: index.html not found</h1><p>Looking at: {index_file}</p>", 
            status_code=404
        )

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
        host="0.0.0.0",
        port=port,
        reload=True
    )
