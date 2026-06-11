import datetime
import ipaddress
import socket
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


BACKEND_DIR = Path(__file__).resolve().parent

print("Generating SSL certificates...")

print("   Generating private key...")
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)
print(f"   Detected local IP: {local_ip}")

subject = issuer = x509.Name(
    [
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Invoice Helper"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ]
)

print("   Building certificate...")
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.DNSName(hostname),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address(local_ip)),
            ]
        ),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)

key_path = BACKEND_DIR / "key.pem"
cert_path = BACKEND_DIR / "cert.pem"

print(f"   Writing {key_path}...")
with key_path.open("wb") as output_file:
    output_file.write(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

print(f"   Writing {cert_path}...")
with cert_path.open("wb") as output_file:
    output_file.write(cert.public_bytes(serialization.Encoding.PEM))

print("")
print("Certificates generated successfully.")
print(f"   - {cert_path}")
print(f"   - {key_path}")
print("")
print("To access from your phone:")
print("   1. Run: python backend/server.py")
print(f"   2. On your phone, go to: https://{local_ip}:8443/scan")
print("   3. Accept the self-signed certificate warning")
print("")
print("Make sure your phone is on the same WiFi network.")
