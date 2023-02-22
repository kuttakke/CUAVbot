from base64 import b64encode
from datetime import datetime
from pathlib import Path
from typing import Any

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import (
    At,
    AtAll,
    Dice,
    Face,
    File,
    Forward,
    Image,
    MarketFace,
    MusicShare,
    Plain,
)
from graiax.text2img.playwright import (
    HTMLRenderer,
    MarkdownConverter,
    PageOption,
    ScreenshotOption,
)
from graiax.text2img.playwright.plugins.code.highlighter import Highlighter
from graiax.text2img.playwright.renderer import BuiltinCSS
from jinja2 import Template
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

from config import settings

# LINK - https://github.com/SAGIRI-kawaii/sagiri-bot/blob/Ariadne-v4/shared/utils/text2img.py


async def html2img(
    html: str,
    page_option: dict[str, Any] | None = None,
    extra_screenshot_option: dict | None = None,
    use_proxy: bool = False,
) -> bytes:
    if not page_option:
        page_option = {
            "viewport": {"width": 600, "height": 10},
            "device_scale_factor": 1.5,
        }
    if use_proxy:
        page_option["proxy"] = {
            "server": f"{settings.proxy.type}://{settings.proxy.host}:{settings.proxy.port}"
        }
    extra_screenshot_option = extra_screenshot_option or {
        "type": "jpeg",
        "quality": 80,
        "scale": "device",
    }
    return await HTMLRenderer(
        css=(
            BuiltinCSS.reset,
            BuiltinCSS.github,
            BuiltinCSS.one_dark,
            BuiltinCSS.container,
            "body {padding: 0 !important}",
        )
    ).render(
        html,
        extra_page_option=PageOption(**page_option),
        extra_screenshot_option=ScreenshotOption(**extra_screenshot_option),
    )


async def md2img(
    markdown: str,
    page_option: dict | None = None,
    extra_screenshot_option: dict | None = None,
    use_proxy: bool = False,
) -> bytes:
    md = (
        MarkdownIt("gfm-like", {"highlight": Highlighter()})
        .use(
            dollarmath_plugin,
            allow_labels=True,
            allow_space=True,
            allow_digits=True,
            double_inline=True,
        )
        .enable("table")
    )
    markdown += (
        "<style>.markdown-body{position:absolute;padding:50px 40px}</style>"
        "<style>.footer{box-sizing:border-box;position:absolute;left:0;width:100%;background:#eee;"
        "padding:50px 40px;margin-top:50px;font-size:0.85rem;color:#6b6b6b;}"
        ".footer p{margin:5px auto;}</style>"
        f'<div class="footer"><p>由 CUAVbot 生成</p><p>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p></div></p></div>'
    )
    res = MarkdownConverter(md).convert(markdown)
    return await html2img(res, page_option, extra_screenshot_option, use_proxy)


async def template2img(
    template: str | Template | Path,
    params: dict,
    page_option: dict | None = None,
    extra_screenshot_option: dict | None = None,
    use_proxy: bool = False,
) -> bytes:
    if isinstance(template, str):
        template = Template(template)
    elif isinstance(template, Path):
        if not template.is_file():
            raise ValueError("Path for template is not a file!")
        template = Template(template.read_text(encoding="utf-8"))
    return await html2img(
        template.render(params), page_option, extra_screenshot_option, use_proxy
    )


async def messagechain2img(
    message: MessageChain,
    img_single_line: bool = False,
    page_option: dict | None = None,
    extra_screenshot_option: dict | None = None,
) -> bytes:
    html = ""
    for i in message.content:
        if isinstance(i, Plain):
            html += i.text.replace("\n", "<br>")
        elif isinstance(i, Image):
            if img_single_line:
                html += "<br>"
            html += f'<img src="data:image/png;base64,{b64encode(await i.get_bytes()).decode("ascii")}" />'
            if img_single_line:
                html += "<br>"
        elif isinstance(i, (Face, MarketFace)):
            html += f"【表情：{i.face_id}】"
        elif isinstance(i, At):
            html += f"@{i.representation}"
        elif isinstance(i, AtAll):
            html += "@全体成员"
        elif isinstance(i, Dice):
            html += f"【骰子：{i.value}】"
        elif isinstance(i, MusicShare):
            html += f"【音乐分享：{i.title}】"
        elif isinstance(i, Forward):
            html += "【转发消息】"
        elif isinstance(i, File):
            html += f"【文件：{i.name}】"
    return await html2img(html.strip("<br>"), page_option, extra_screenshot_option)
