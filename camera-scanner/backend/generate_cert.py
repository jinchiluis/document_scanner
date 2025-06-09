from pathlib import Path
import subprocess
import sys

CERT_FILE = Path(__file__).with_name('cert.pem')
KEY_FILE = Path(__file__).with_name('key.pem')

if CERT_FILE.exists() and KEY_FILE.exists():
    print(f"Certificate already exists: {CERT_FILE} and {KEY_FILE}")
    sys.exit(0)

cmd = [
    'openssl',
    'req',
    '-x509',
    '-newkey', 'rsa:4096',
    '-keyout', str(KEY_FILE),
    '-out', str(CERT_FILE),
    '-days', '365',
    '-nodes',
    '-subj', '/CN=localhost'
]

print('Generating self-signed certificate...')
try:
    subprocess.run(cmd, check=True)
    print(f'Certificate generated: {CERT_FILE}')
except FileNotFoundError:
    print('Error: openssl not found. Please install openssl to generate certificates.')
    sys.exit(1)
