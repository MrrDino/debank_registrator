import time
import asyncio
import functools

from loguru import logger


def async_retry(func):

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):

        while True:
            try:
                return await func(*args, **kwargs)
            except Exception as err:
                logger.error(f"Retry, error - {err}")
                await asyncio.sleep(25)

    return wrapper


def sync_retry(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        while True:
            try:
                return func(*args, **kwargs)
            except Exception as err:
                logger.error(f"Retry, error - {err}")
                time.sleep(25)

    return wrapper
