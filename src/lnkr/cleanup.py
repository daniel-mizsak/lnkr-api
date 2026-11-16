"""
Clean up unnecessary database entries.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

import asyncio

from lnkr.database import AsyncSessionLocal, engine
from lnkr.database.tokens.login_token_database import clean_up_login_tokens
from lnkr.database.tokens.refresh_token_database import clean_up_refresh_tokens


def main() -> None:
    """Clean up unnecessary database entries."""
    asyncio.run(_clean_up())


async def _clean_up() -> None:
    try:
        await _clean_up_login_and_refresh_tokens()
    finally:
        await engine.dispose()


async def _clean_up_login_and_refresh_tokens() -> None:
    async with AsyncSessionLocal.begin() as session:
        await clean_up_login_tokens(session)
        await clean_up_refresh_tokens(session)


if __name__ == "__main__":
    main()
