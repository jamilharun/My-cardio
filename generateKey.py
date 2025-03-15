from cryptography.fernet import Fernet

# Generate a new secret key
key = Fernet.generate_key().decode()

print(f"Your Fernet Secret Key: {key}")
