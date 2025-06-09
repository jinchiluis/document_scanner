from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import socket
import subprocess
import os
import sys

app = FastAPI()

# Path to camera-scanner folder
frontend_dir = Path(__file__).resolve().parent / "camera-scanner"

# Create saved_docs folder
SAVE_DIR = Path(__file__).resolve().parent / "saved_docs"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
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
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)

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

def create_cert_with_openssl():
    """Create certificate using OpenSSL if available"""
    try:
        local_ip = get_local_ip()
        
        # Create OpenSSL config for IP address
        config_content = f"""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
CN = {local_ip}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = {local_ip}
IP.2 = 127.0.0.1
"""
        
        with open("cert_config.conf", "w") as f:
            f.write(config_content)
        
        # Generate certificate
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", 
            "-keyout", "server_key.pem", "-out", "server_cert.pem", 
            "-days", "30", "-nodes", "-config", "cert_config.conf", 
            "-extensions", "v3_req"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return "server_cert.pem", "server_key.pem"
        else:
            print(f"OpenSSL error: {result.stderr}")
            return None, None
            
    except Exception as e:
        print(f"Error with OpenSSL: {e}")
        return None, None

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    
    print("🚀 Starting Document Scanner Server...")
    
    # Try to create HTTPS first
    cert_file = "server_cert.pem"
    key_file = "server_key.pem"
    
    # Method 1: Try with existing certificates
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("📜 Using existing certificates...")
        use_https = True
    else:
        # Method 2: Try to create with OpenSSL
        print("📜 Creating new certificates...")
        cert_file, key_file = create_cert_with_openssl()
        use_https = cert_file is not None
    
    if use_https and cert_file and os.path.exists(cert_file):
        print("=" * 60)
        print("🔒 HTTPS SERVER STARTING...")
        print("=" * 60)
        print(f"📱 Phone URL: https://{local_ip}:{port}")
        print("🖥️  PC URL: https://127.0.0.1:{port}")
        print("=" * 60)
        print("📱 PHONE INSTRUCTIONS:")
        print("1. Open Chrome on your phone")
        print(f"2. Go to: https://{local_ip}:{port}")
        print("3. You'll see 'Your connection is not private'")
        print("4. Click 'Advanced'")
        print("5. Click 'Proceed to [IP] (unsafe)'")
        print("6. Allow camera when prompted")
        print("=" * 60)
        
        try:
            uvicorn.run(
                "server:app",
                host="0.0.0.0",
                port=port,
                ssl_keyfile=key_file,
                ssl_certfile=cert_file,
                log_level="info"
            )
        except Exception as e:
            print(f"❌ HTTPS failed: {e}")
            print("🔄 Falling back to HTTP...")
            use_https = False
    
    if not use_https:
        print("=" * 60)
        print("📡 HTTP SERVER (Limited Mobile Support)")
        print("=" * 60)
        print(f"🖥️  PC: http://127.0.0.1:{port}")
        print(f"📱 Phone: http://{local_ip}:{port}")
        print("⚠️  Camera may not work on mobile over HTTP")
        print("=" * 60)
        
        uvicorn.run(
            "server:app",
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
