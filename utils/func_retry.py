""" 方法重试decorator """
import asyncio
import time
from functools import wraps

from loguru import logger


def retry(
    times: int = 3, delay: int = 1, backoff: int = 2, exceptions: tuple = (Exception,)
):
    """Decorator to retry a function/method if an exception occurs.

    :param times: Number of times to retry (not including the first attempt).
    :param delay: Initial delay between retries in seconds.
    :param backoff: Backoff multiplier e.g. value of 2 will double the delay each retry.
    :param exceptions: Tuple of exceptions to check. May be a tuple of
        exception classes or a tuple of tuples of exception classes and
        arguments to pass to the exception constructor.
    :return: The return value of the function that was retried.
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = times, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{f.__name__}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


# async version


def aretry(
    times: int = 3, delay: int = 1, backoff: int = 2, exceptions: tuple = (Exception,)
):
    """Decorator to retry a function/method if an exception occurs.

    :param times: Number of times to retry (not including the first attempt).
    :param delay: Initial delay between retries in seconds.
    :param backoff: Backoff multiplier e.g. value of 2 will double the delay each retry.
    :param exceptions: Tuple of exceptions to check. May be a tuple of
        exception classes or a tuple of tuples of exception classes and
        arguments to pass to the exception constructor.
    :return: The return value of the function that was retried.
    """

    def deco_retry(f):
        @wraps(f)
        async def f_retry(*args, **kwargs):
            mtries, mdelay = times, delay
            while mtries > 1:
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{f.__name__}, Retrying in {mdelay} seconds..."
                    logger.warning(msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return await f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


if __name__ == "__main__":

    # @retry()
    # def test():
    #     print("test")
    #     raise RuntimeError("test")

    # test()

    @aretry()
    async def atest():
        print("test")
        raise RuntimeError("test")

    asyncio.run(atest())
