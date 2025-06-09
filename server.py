from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import socket
import ssl
import tempfile
import os

app = FastAPI()

# Path to camera-scanner folder
frontend_dir = Path(__file__).resolve().parent / "camera-scanner"
print(f"Serving files from: {frontend_dir}")

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

def create_simple_cert():
    """Create a simple self-signed certificate using Python"""
    try:
        # Try to use cryptography library
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime as dt
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Get local IP for certificate
        local_ip = get_local_ip()
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            dt.datetime.utcnow()
        ).not_valid_after(
            dt.datetime.utcnow() + dt.timedelta(days=30)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(local_ip),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Save certificate and key
        cert_file = "mobile_cert.pem"
        key_file = "mobile_key.pem"
        
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        return cert_file, key_file
        
    except ImportError:
        print("❌ cryptography library not found.")
        print("📦 Install with: pip install cryptography")
        return None, None
    except Exception as e:
        print(f"❌ Error creating certificate: {e}")
        return None, None

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    
    print("🔒 Setting up HTTPS for mobile camera access...")
    
    # Try to create or use existing certificates
    cert_file = "mobile_cert.pem"
    key_file = "mobile_key.pem"
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("📜 Creating SSL certificate...")
        cert_file, key_file = create_simple_cert()
    
    if cert_file and key_file and os.path.exists(cert_file):
        print("=" * 60)
        print("🔒 HTTPS MOBILE DOCUMENT SCANNER READY!")
        print("=" * 60)
        print(f"📱 Phone Access: https://{local_ip}:{port}")
        print("=" * 60)
        print("📋 Instructions:")
        print("1. Make sure your phone and PC are on the same WiFi")
        print("2. Open Chrome on your phone")
        print(f"3. Go to: https://{local_ip}:{port}")
        print("4. You'll see a security warning - this is normal!")
        print("5. Click 'Advanced' then 'Proceed to [IP address]'")
        print("6. Allow camera access when prompted")
        print("7. Start scanning documents! 📄")
        print("=" * 60)
        print("⚠️  Security Warning Expected:")
        print("   Your browser will show 'Not Secure' - that's normal")
        print("   for self-signed certificates. Just proceed anyway.")
        print("=" * 60)
        
        # Run HTTPS server
        uvicorn.run(
            "server:app",
            host="0.0.0.0",
            port=port,
            ssl_keyfile=key_file,
            ssl_certfile=cert_file,
            reload=False  # Disable reload for HTTPS
        )
    else:
        print("❌ Could not create HTTPS certificate.")
        print("📦 Please install: pip install cryptography")
        print("🔄 Falling back to HTTP...")
        print(f"📱 Try: http://{local_ip}:{port} (may not work on mobile)")
        
        uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
