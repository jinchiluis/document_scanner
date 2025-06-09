from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import base64
from datetime import datetime
from pathlib import Path
import uvicorn
import ssl
import json

app = FastAPI()

# Get the project root directory (parent of backend folder)
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

# Setup paths
SAVE_DIR = BACKEND_DIR / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Backend directory: {BACKEND_DIR}")
print(f"📁 Project root: {PROJECT_ROOT}")
print(f"📁 Save directory: {SAVE_DIR}")

# Serve the HTML file at root
@app.get("/")
async def serve_index():
    index_path = PROJECT_ROOT / "index.html"
    print(f"Serving index.html from: {index_path}")
    if not index_path.exists():
        return HTMLResponse(content="<h1>index.html not found!</h1><p>Make sure index.html is in the project root directory.</p>", status_code=404)
    return FileResponse(index_path)

# Serve CSS file
@app.get("/static/styles.css")
async def serve_styles():
    styles_path = PROJECT_ROOT / "styles.css"
    if not styles_path.exists():
        return HTMLResponse(content="/* styles.css not found */", status_code=404)
    return FileResponse(styles_path)

# Serve JS file
@app.get("/static/script.js")
async def serve_script():
    script_path = PROJECT_ROOT / "script.js"
    if not script_path.exists():
        return HTMLResponse(content="// script.js not found", status_code=404)
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
        return JSONResponse({
            "status": "saved", 
            "file": str(filename), 
            "timestamp": timestamp
        })
    except Exception as e:
        print(f"❌ Error saving image: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "save_dir": str(SAVE_DIR)}

if __name__ == "__main__":
    print("\n🚀 Starting Document Scanner Server...")
    
    # Check if we have SSL certificates
    cert_path = BACKEND_DIR / "cert.pem"
    key_path = BACKEND_DIR / "key.pem"
    cert_exists = cert_path.exists() and key_path.exists()
    
    if cert_exists:
        print(f"🔒 SSL certificates found!")
        print(f"   - Certificate: {cert_path}")
        print(f"   - Private key: {key_path}")
        print(f"\n📱 Starting HTTPS server...")
        print(f"✅ Access the app at: https://localhost:8443")
        print(f"✅ From your phone use: https://YOUR_COMPUTER_IP:8443")
        print(f"   (Replace YOUR_COMPUTER_IP with your actual IP address)")
        print(f"\n⚠️  Your browser will show a security warning - this is normal for self-signed certificates.")
        print(f"   Click 'Advanced' and 'Proceed' to continue.\n")
        
        try:
            uvicorn.run(
                app, 
                host="0.0.0.0", 
                port=8443, 
                ssl_keyfile=str(key_path), 
                ssl_certfile=str(cert_path),
                log_level="info"
            )
        except Exception as e:
            print(f"\n❌ Error starting HTTPS server: {e}")
            print("Falling back to HTTP...")
            
    else:
        print(f"\n⚠️  No SSL certificates found!")
        print(f"   Expected locations:")
        print(f"   - {cert_path}")
        print(f"   - {key_path}")
        print(f"\n💡 To enable HTTPS (required for mobile camera access):")
        print(f"   Run: python generate_cert.py")
        print(f"\n📱 Starting HTTP server instead...")
        print(f"✅ Access the app at: http://localhost:8000")
        print(f"⚠️  Note: Camera access won't work on mobile devices without HTTPS!\n")
        
        try:
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        except Exception as e:
            print(f"\n❌ Error starting server: {e}")
            print("\nPossible issues:")
            print("1. Port might be in use - try closing other applications")
            print("2. Missing dependencies - run: pip install fastapi uvicorn")
            import traceback
            traceback.print_exc()
