from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import ipaddress
import socket

print("🔐 Generating SSL certificates...")

# Generate private key
print("   Generating private key...")
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Get local IP address
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
print(f"   Detected local IP: {local_ip}")

# Create certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"State"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"City"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Camera Scanner"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
])

# Build certificate
print("   Building certificate...")
cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([
        x509.DNSName(u"localhost"),
        x509.DNSName(hostname),
        x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address(local_ip)),
    ]),
    critical=False,
).sign(key, hashes.SHA256())

# Write private key
print("   Writing key.pem...")
with open("key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Write certificate
print("   Writing cert.pem...")
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("\n✅ Certificates generated successfully!")
print(f"   - cert.pem (certificate file)")
print(f"   - key.pem (private key file)")
print(f"\n📱 To access from your phone:")
print(f"   1. Run: python server.py")
print(f"   2. On your phone, go to: https://{local_ip}:8443")
print(f"   3. Accept the security warning (it's a self-signed certificate)")
print(f"\n💡 Make sure your phone is on the same WiFi network!")
