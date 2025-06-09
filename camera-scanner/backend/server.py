from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import base64
from datetime import datetime
from pathlib import Path
import uvicorn
import ssl

app = FastAPI()

# Get the project root directory (parent of backend folder)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Setup paths
SAVE_DIR = BACKEND_DIR / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Serve the HTML file at root
@app.get("/")
async def serve_index():
    index_path = PROJECT_ROOT / "index.html"
    return FileResponse(index_path)

# Serve CSS file
@app.get("/static/styles.css")
async def serve_styles():
    styles_path = PROJECT_ROOT / "styles.css"
    return FileResponse(styles_path)

# Serve JS file
@app.get("/static/script.js")
async def serve_script():
    script_path = PROJECT_ROOT / "script.js"
    return FileResponse(script_path)

# Handle image saving
@app.post("/save-image")
async def save_image(req: Request):
    try:
        data = await req.json()
        img_data = data['image'].split(',')[1]
        img_bytes = base64.b64decode(img_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = SAVE_DIR / f"doc_{timestamp}.png"
        
        with open(filename, 'wb') as f:
            f.write(img_bytes)
            
        print(f"✅ Saved image: {filename}")
        return {"status": "saved", "file": str(filename), "timestamp": timestamp}
    except Exception as e:
        print(f"❌ Error saving image: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Check if we have SSL certificates
    cert_exists = (BACKEND_DIR / "cert.pem").exists() and (BACKEND_DIR / "key.pem").exists()
    
    if cert_exists:
        print(f"🔒 Starting HTTPS server...")
        print(f"📁 Project root: {PROJECT_ROOT}")
        print(f"📁 Save directory: {SAVE_DIR}")
        print(f"\n✅ Access the app at: https://0.0.0.0:8443")
        print(f"📱 From your phone use: https://YOUR_COMPUTER_IP:8443")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8443, 
            ssl_keyfile=str(BACKEND_DIR / "key.pem"), 
            ssl_certfile=str(BACKEND_DIR / "cert.pem")
        )
    else:
        print("\n⚠️  No SSL certificates found!")
        print("Run generate_cert.py first to create certificates.")
        print("\nStarting HTTP server instead (camera won't work on mobile)...")
        print(f"📁 Project root: {PROJECT_ROOT}")
        print(f"📁 Save directory: {SAVE_DIR}")
        print(f"\n Access the app at: http://0.0.0.0:8000")
        
        uvicorn.run(app, host="0.0.0.0", port=8000)
