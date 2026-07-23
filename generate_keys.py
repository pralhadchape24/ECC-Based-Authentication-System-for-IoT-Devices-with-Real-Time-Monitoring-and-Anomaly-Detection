from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import sys


device_id = sys.argv[1] if len(sys.argv) > 1 else "ESP001"

private_key = ec.generate_private_key(ec.SECP256R1())
public_key  = private_key.public_key()

with open(f"private_key_{device_id}.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

with open(f"public_key_{device_id}.pem", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

print(f"Keys generated for {device_id}:")
print(f"  private_key_{device_id}.pem  ← flash this to ESP32")
print(f"  public_key_{device_id}.pem   ← register this on server")