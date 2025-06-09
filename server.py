from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
from datetime import datetime
from pathlib import Path
import uvicorn
import ssl

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

if __name__ == "__main__":
    # Create SSL context for HTTPS
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # You'll need to generate these certificate files first
    # Run this command in terminal:
    # openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
    
    try:
        ssl_context.load_cert_chain("cert.pem", "key.pem")
        print("Starting HTTPS server on https://0.0.0.0:8443")
        print("Access from phone using: https://YOUR_COMPUTER_IP:8443")
        uvicorn.run(app, host="0.0.0.0", port=8443, ssl_version=ssl.PROTOCOL_TLS_SERVER, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
    except FileNotFoundError:
        print("\n⚠️  Certificate files not found!")
        print("Generate them with this command:")
        print("openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes\n")
        print("For now, starting HTTP server (camera won't work on mobile)")
        uvicorn.run(app, host="0.0.0.0", port=8000)
