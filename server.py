from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import ssl
import tempfile
import os

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

def create_self_signed_cert():
    """Create a self-signed certificate using Python's ssl module"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
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
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.IPAddress("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key to files
        cert_file = "cert.pem"
        key_file = "key.pem"
        
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
        print("cryptography library not installed. Install with: pip install cryptography")
        return None, None

if __name__ == "__main__":
    print("Starting HTTPS server...")
    
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    # Check if certificates exist
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("Creating self-signed certificate...")
        cert_file, key_file = create_self_signed_cert()
        
        if cert_file is None:
            print("Could not create certificate. Falling back to HTTP...")
            print("To use HTTPS, install: pip install cryptography")
            print("Starting HTTP server instead...")
            uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
        else:
            print("Certificate created successfully!")
    
    if cert_file and key_file and os.path.exists(cert_file):
        print("Starting HTTPS server on https://127.0.0.1:8000")
        print("You'll see a security warning - click 'Advanced' then 'Proceed'")
        uvicorn.run(
            "server:app",
            host="127.0.0.1", 
            port=8000,
            ssl_keyfile=key_file,
            ssl_certfile=cert_file,
            reload=True
        )
    else:
        print("Starting HTTP server on http://127.0.0.1:8000")
        uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
