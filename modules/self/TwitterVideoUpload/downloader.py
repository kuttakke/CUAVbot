import asyncio
import re
from pathlib import Path

import aiofile
from aiohttp.client_exceptions import ContentTypeError
from loguru import logger

from utils.session import Session


class TwitterVideoDownloader:
    PATH_BEARER_TOKEN = Path(__file__).parent / "bearer_token.txt"

    RGX_BEARER_TOKEN = r"Bearer ([a-zA-Z0-9%-])+"
    URL_BEARER_TOKEN = "https://abs.twimg.com/web-video-player/TwitterVideoPlayerIframe.cefd459559024bfb.js"
    URL_GUEST_TOKEN = "https://api.twitter.com/1.1/guest/activate.json"
    URL_VIDEO_INFO = "https://api.twitter.com/1.1/videos/tweet/config/{}.json"
    URL_VIDEO_FILE = "https://video.twimg.com"
    RGX_M3U8 = '/[^"?\n]+'
    RGX_M4S = '/amplify_video[^"\n]+'

    BEARER_TOKEN = ""
    GUEST_TOKEN = ""

    @classmethod
    async def init(cls):
        if cls.PATH_BEARER_TOKEN.exists():
            cls.BEARER_TOKEN = cls.PATH_BEARER_TOKEN.read_text()
        else:
            await cls.get_bearer_token()
            cls.PATH_BEARER_TOKEN.write_text(cls.BEARER_TOKEN)

    @classmethod
    async def get_bearer_token(cls):
        cls.BEARER_TOKEN = re.search(
            cls.RGX_BEARER_TOKEN,
            (await Session.request("GET", cls.URL_BEARER_TOKEN, response_type="text")),
        )[  # type: ignore
            0
        ]

    @classmethod
    async def get_guest_token(cls, retry: bool = False):
        data = await Session.request(
            "POST",
            cls.URL_GUEST_TOKEN,
            response_type="json",
            headers={"Authorization": cls.BEARER_TOKEN},
        )
        if data.get("errors", None):
            if retry:
                raise BearerTokenError(
                    f"请求guest_token失败\n{data['errors'][0]['message']}"
                )
            await cls.get_bearer_token()
            await cls.get_guest_token(True)
            return

        cls.GUEST_TOKEN = data["guest_token"]

    @classmethod
    async def get_m3u8_urls(cls, tweet_id: str, retry: bool = False) -> str:
        try:
            data = await Session.request(
                "GET",
                cls.URL_VIDEO_INFO.format(tweet_id),
                response_type="json",
                headers={
                    "Authorization": cls.BEARER_TOKEN,
                    "x-guest-token": cls.GUEST_TOKEN,
                },
                data={"client": "web"},
            )
        except ContentTypeError as e:
            raise InvalidTweet("无效的推文") from e

        if data.get("errors", None):
            if retry:
                raise GuestTokenError(f"请求m3u8_urls失败\n{data['errors'][0]['message']}")
            await cls.get_guest_token()
            return await cls.get_m3u8_urls(tweet_id, True)
        return data["track"]["playbackUrl"].split("?")[0]

    @classmethod
    async def get_m3u8_url(cls, m3u8_url: str) -> str:
        return re.findall(
            cls.RGX_M3U8, await Session.request("GET", m3u8_url, response_type="text")
        )[-1]

    @classmethod
    async def convert_m3u8_to_mp4_ffmpeg(cls, m3u8_url: str, twid: str) -> Path:
        path = Path(__file__).parent / "video" / f"tw-{twid}.mp4"
        process = await asyncio.create_subprocess_shell(
            f"ffmpeg -i {m3u8_url} -c copy {path} -hide_banner",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return_code = await process.wait()
        if return_code != 0:
            logger.error(f"转化失败，返回码：{return_code}")
            stdout, stderr = await process.communicate()
            logger.error(stdout.decode("utf-8"))
            logger.error(stderr.decode("utf-8"))
            if path.exists():
                path.unlink()
            raise FFmpegError("转化失败")

        return path

    @classmethod
    async def convert_m3u8_to_mp4(cls, m3u8_url: str) -> bytes:
        url_list = re.findall(
            cls.RGX_M4S, (await Session.request("GET", m3u8_url, response_type="text"))
        )
        return b"".join(
            await asyncio.gather(
                *[
                    Session.request(
                        "GET", cls.URL_VIDEO_FILE + url, response_type="bytes"
                    )
                    for url in url_list
                ]
            )
        )

    @classmethod
    async def read_video(cls, path: Path) -> bytes:
        async with aiofile.async_open(path, "rb") as f:
            return await f.read()

    @classmethod
    async def get_video(cls, tweet_id: str) -> bytes:
        if (path := Path(__file__).parent / "video" / f"tw-{tweet_id}.mp4").exists():
            return await cls.read_video(path)
        await cls.get_bearer_token()
        await cls.get_guest_token()
        m3u8_url = await cls.get_m3u8_url(await cls.get_m3u8_urls(tweet_id))
        return await cls.read_video(
            await cls.convert_m3u8_to_mp4_ffmpeg(
                f"{cls.URL_VIDEO_FILE}{m3u8_url}", tweet_id
            )
        )


class BearerTokenError(Exception):
    ...


class GuestTokenError(Exception):
    ...


class FFmpegError(Exception):
    ...


class InvalidTweet(Exception):
    ...
