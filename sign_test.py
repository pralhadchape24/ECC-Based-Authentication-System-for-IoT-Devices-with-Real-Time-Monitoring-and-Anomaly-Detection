from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import base64

challenge = input("Enter challenge: ")

with open("private_key.pem", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

signature = private_key.sign(
    challenge.encode(),
    ec.ECDSA(hashes.SHA256())
)

print("Signature (base64):")
print(base64.b64encode(signature).decode())