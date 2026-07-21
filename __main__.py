#!/usr/bin/env python3
import os

from backends.confluence.client import ConfluenceClient
from backends.confluence.confluence import Confluence

try:
    import dotenv
except ImportError:
    dotenv = None  # type: ignore[assignment]


def main() -> None:
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        raise ValueError("CONFLUENCE_TOKEN environment variable not set")
    base_url = os.environ.get("CONFLUENCE_URL", "https://confluence.shopee.io").rstrip(
        "/"
    )
    client = ConfluenceClient(base_url=base_url, token=token)
    conf = Confluence(client)
    conf.main()


if __name__ == "__main__":
    if dotenv is not None:
        dotenv.load_dotenv()
    main()
