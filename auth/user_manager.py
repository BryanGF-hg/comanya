import hashlib

class AuthSystem:
    def __init__(self):
        # En un entorno real, esto iría en una base de datos o config.yaml cifrado
        self.users = {
            "admin": {"password": "hash_password", "level": "admin"},
            "comercial1": {"password": "hash_password", "level": "user"}
        }

    def login(self, username, password):
        if username in self.users and self._verify(password, self.users[username]['password']):
            return self.users[username]['level']
        return None

    def _verify(self, pwd, pwd_hash):
        return hashlib.sha256(pwd.encode()).hexdigest() == pwd_hash