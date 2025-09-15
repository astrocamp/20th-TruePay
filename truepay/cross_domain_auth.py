from django.core.signing import Signer, BadSignature
from django.conf import settings
import time
import json


class CrossDomainAuth:
    def __init__(self):
        self.signer = Signer()
        self.token_lifetime = 120

    def generate_auth_token(self, user, target_url):
        data = {"user_id": user.id, "timestamp": time.time(), "target_url": target_url}
        token = self.signer.sign_object(data)
        return token

    def verify_auth_token(self, token):
        try:
            data = self.signer.unsign_object(token)
            current_time = time.time()
            token_age = current_time - data["timestamp"]

            if token_age > self.token_lifetime:
                return None
            return data
        except BadSignature:
            return None
        except (KeyError, TypeError):
            return None
