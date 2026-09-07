"""HTTPS helpers for source and frozen builds, with verification always enabled."""

import ssl
from urllib.request import HTTPSHandler, build_opener

import certifi


def create_https_context():
    # Preserve system/explicit administrator trust and add the bundled public
    # roots. python.org builds can point to a CA file absent on the recipient Mac.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def create_https_opener(*handlers):
    return build_opener(HTTPSHandler(context=create_https_context()), *handlers)
