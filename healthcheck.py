"""
Health check script for the docker image.

@author "Daniel Mizsak" <info@pythonvilag.hu>
"""

import sys

# TODO: This assumes that httpx is installed in the production image as a dependency of fastapi.
import httpx
from fastapi import status


def main() -> int:
    """Perform api health check."""
    url = "http://127.0.0.1:8000/v1/health"
    try:
        with httpx.Client(timeout=3) as client:
            response = client.get(url)
    except httpx.RequestError:
        return 1

    if response.status_code != status.HTTP_200_OK:
        return 1

    data = response.json()
    confirm_message = data.get("message") == "lnkr api running"
    confirm_database = data.get("database") is True
    confirm_cache = data.get("cache") is True
    if not (confirm_message and confirm_database and confirm_cache):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
