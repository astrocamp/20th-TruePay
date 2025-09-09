import os
from django.core.cache import cache


def get_allowed_hosts():
    base_hosts = [
        "127.0.0.1",
        "localhost",
    ]

    ngrok_url = os.getenv("NGROK_URL")
    if ngrok_url:
        base_hosts.append(ngrok_url)
    try:
        from django.apps import apps

        if apps.ready:
            MerchantOwnDomain = apps.get_model("merchant_account", "MerchantOwnDomain")
            custom_domains = MerchantOwnDomain.objects.filter(
                is_verified=True, is_active=True
            ).values_list("domain_name", flat=True)
            base_hosts.extend(list(custom_domains))
    except Exception as e:
        print(f"Warning: Could not load custom domains: {e}")
        pass
    return base_hosts
