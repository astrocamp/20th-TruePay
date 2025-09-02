import random
import string
from .models import Merchant


def generate_unique_subdomain():
    max_attempts = 100
    attempts = 0

    while attempts < max_attempts:
        subdomain = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))

        if not Merchant.objects.filter(subdomain=subdomain).exists():
            return subdomain

        attempts += 1

    raise ValueError("無法生成唯一的subdomain,請再試一次")
