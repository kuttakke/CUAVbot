from loguru import logger

from utils.session import Session


class TokenHandler:
    headers = {"User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"}
    client_id = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
    client_secret = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
    login_url = "https://oauth.secure.pixiv.net/auth/token"

    @classmethod
    async def fetch(cls, data: dict) -> dict:
        max_try_count = 3
        error_proxy = None
        error_not_proxy = None
        while max_try_count:
            try:
                async with Session.proxy_session.post(
                    cls.login_url, data=data, headers=cls.headers
                ) as res:
                    return await res.json()
            except Exception as e:
                error_proxy = e
                logger.error("can't get token with proxy, try no to use proxy")
                try:
                    async with Session.session.request(
                        "POST", cls.login_url, data=data, headers=cls.headers
                    ) as res:
                        return await res.json()
                except Exception as e:
                    error_not_proxy = e
                    logger.error("can't get token without proxy'")
            max_try_count -= 1
            logger.info(f"retry left {max_try_count} times")
        raise error_proxy or error_not_proxy or Exception("unknown error")

    @classmethod
    async def refresh_token(cls, refresh_token: str) -> tuple[str, str]:
        """
        refresh old token
        :param refresh_token:
        :return: access_token, refresh_token
        """
        data = {
            "client_id": cls.client_id,
            "client_secret": cls.client_secret,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        }
        token = await cls.fetch(data)
        return token["access_token"], token["refresh_token"]
