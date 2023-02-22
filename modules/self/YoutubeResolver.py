import re
from datetime import datetime
from pathlib import Path

from aiohttp import ClientTimeout
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import Group, GroupMessage, MessageChain
from graia.ariadne.message.element import Image, Plain
from graiax.shortcut.saya import decorate, listen
from pydantic import BaseModel

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.session import Session
from utils.t2i import md2img
from utils.tool import to_module_file_name

module_name = "油管视频链接解析"
_API = "https://www.googleapis.com/youtube/v3/videos"
_KEY = "你的油管APIKey"
_REGEX = r"(?:https?:)?(?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtu\.be\/|youtube(?:-nocookie)?\.com\S*?[^\w\s-])([\w-]{11})(?=[^\w-]|$)(?![?=&+%\w.-]*(?:['\"][^<>]*>|<\/a>))[?=&+%\w.-]*"
_Thumbnail = ("standard", "high", "medium", "default")
module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="kutake",
    description="解析Youtube链接",
)
channel = Controller.module_register(module)


class Statistic(BaseModel):
    viewCount: int
    likeCount: int
    favoriteCount: int
    commentCount: int


class Video(BaseModel):
    title: str
    url: str
    publishedAt: str
    channelId: str
    channelTitle: str
    description: str
    thumbnail: str
    statistics: Statistic


class ResolverException(Exception):
    pass


def _get_thumbnails(data: dict) -> str:
    for i in _Thumbnail:
        if i in data:
            return data[i]["url"]
    return data["default"]["url"]


async def _get_video_info(id: str, _retry: int = 0) -> Video:
    try:
        async with Session.proxy_session.get(
            _API,
            params={
                "part": "snippet,statistics",
                "id": id,
                "key": _KEY,
            },
            timeout=ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                raise ResolverException(f"API返回错误,状态码:{str(resp.status)}")
            data = (await resp.json())["items"][0]
            return Video(
                title=data["snippet"]["title"],
                url=f"https://www.youtube.com/watch?v={id}",
                publishedAt=data["snippet"]["publishedAt"],
                channelId=data["snippet"]["channelId"],
                channelTitle=data["snippet"]["channelTitle"],
                description=data["snippet"]["description"].replace("\n", "<br/>"),
                thumbnail=_get_thumbnails(data["snippet"]["thumbnails"]),
                statistics=Statistic(
                    viewCount=int(data["statistics"]["viewCount"]),
                    likeCount=int(data["statistics"]["likeCount"]),
                    favoriteCount=int(data["statistics"]["favoriteCount"]),
                    commentCount=int(data["statistics"]["commentCount"]),
                ),
            )
    except Exception as e:
        if _retry < 3:
            return await _get_video_info(id, _retry + 1)
        raise e


async def _make_img(video: Video) -> bytes:
    md = (
        f"<div align=center><img src='{video.thumbnail}'/></div>\n\n"
        f"<div align=center><h1>{video.title}</h1></div>\n\n"
        f"频道: {video.channelTitle}  \n\n"
        f"发布时间: {video.publishedAt}  \n\n"
        f"{video.statistics.viewCount} 次观看  {video.statistics.likeCount} 个赞  \n\n"
        f"{video.statistics.commentCount} 条评论  {video.statistics.favoriteCount} 个收藏  \n\n"
        "\n\n---\n\n"
        f"### 简介\n\n{video.description}"
    )
    return await md2img(md)


@listen(GroupMessage)
@decorate(BlackList.require(module_name))
async def youtube_resolver(app: Ariadne, message: MessageChain, group: Group):
    if not (match := re.search(_REGEX, message.display)):
        return
    try:
        video = await _get_video_info(match[1])
    except Exception as e:
        await app.send_group_message(group, MessageChain(f"解析失败: {e}"))
        return
    await app.send_group_message(
        group,
        MessageChain(
            [
                Image(data_bytes=await _make_img(video)),
                Plain(f"{video.title}\n{video.url}"),
            ]
        ),
    )
