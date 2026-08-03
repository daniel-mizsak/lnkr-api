"""
Fixtures used in testing the cache.

Copyright (C) 2026 "Daniel Mizsak" <daniel@mizsak.com>
"""

from typing import TYPE_CHECKING, cast

import pytest
from fakeredis import FakeAsyncRedis

if TYPE_CHECKING:
    from redis.asyncio import Redis


@pytest.fixture(name="cache")
def cache_fixture() -> Redis:
    return cast("Redis", FakeAsyncRedis(decode_responses=True))
