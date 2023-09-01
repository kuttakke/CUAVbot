import re
from pathlib import Path

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import (
    GroupMessage,
    MessageEvent,
)
from graia.ariadne.message.parser.twilight import (
    MatchResult,
    RegexMatch,
    SpacePolicy,
    Twilight,
)
from graiax.shortcut.saya import decorate, dispatch, listen

from core.control import Controller, Modules
from core.depend.blacklist import BlackList
from utils.tool import to_module_file_name

from .downloader import TwitterVideoDownloader

module_name = "推特视频上传"
module = Modules(
    name=module_name,
    file_name=to_module_file_name(Path(__file__)),
    author="Kutake",
    description="使用Twittervdo下载推特视频",
    usage="发送推特链接即可",
    example="https://twitter.com/xxx/status/xxx",
)
channel = Controller.module_register(module)

Match = Twilight(
    [
        RegexMatch(r"[.。!！](twitter|推特)").space(SpacePolicy.PRESERVE),
        RegexMatch("https://twitter.com/.*/status/.*") @ "url",
    ]
)


@listen(GroupMessage)
@dispatch(Match)
@decorate(BlackList.require(module_name))
async def get_video(app: Ariadne, event: MessageEvent, url: MatchResult):
    match = re.search(r"/status/(\d+)[\D]?", str(url.result).strip())
    assert match, "解析失败"
    try:
        video_data = await TwitterVideoDownloader.get_video(match[1])
    except Exception as e:
        await app.send_group_message(event.sender.group, str(e))  # type: ignore
        raise e
    await app.upload_file(
        data=video_data, target=event.sender.group, name=f"tw-{match[1]}.mp4"  # type: ignore
    )
