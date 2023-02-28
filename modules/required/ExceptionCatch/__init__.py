# LINK - https://github.com/I-love-study/A_Simple_QQ_Bot/blob/Ariadne_Version/modules/basic/exception_catch.py
from io import StringIO
from pathlib import Path

from graia.ariadne import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.broadcast.builtin.event import ExceptionThrowed
from graiax.shortcut.saya import listen
from rich.console import Console
from rich.traceback import Traceback

from config import settings
from core.control import Controller
from core.entity import Modules
from utils.msgtool import send_debug
from utils.t2i import html2img
from utils.tool import to_module_file_name

module_name = "错误捕获"

module = Modules(
    name=module_name,
    author="I-love-study",
    description="捕获错误并将其转为图片发送的插件",
    file_name=to_module_file_name(Path(__file__)),
)
channel = Controller.module_register(module)

CONSOLE_SVG_FORMAT = """\
<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Regular"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff") format("woff");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Bold"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff") format("woff");
        font-style: bold;
        font-weight: 700;
    }}
    .{unique_id}-matrix {{
        font-family: Fira Code, 思源黑体, monospace;
        font-size: {char_height}px;
        line-height: {line_height}px;
        font-variant-east-asian: full-width;
    }}
    .{unique_id}-title {{
        font-size: 18px;
        font-weight: bold;
        font-family: arial;
    }}
    {styles}
    </style>
    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />
    </clipPath>
    {lines}
    </defs>
    {chrome}
    <g transform="translate({terminal_x}, {terminal_y})" clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
    </g>
    </g>
</svg>
"""


@listen(ExceptionThrowed)
async def except_handle(event: ExceptionThrowed):
    c = Console(file=StringIO(), record=True)
    t = Traceback.from_exception(
        type(event.exception),
        event.exception,
        event.exception.__traceback__,
        show_locals=True,
    )
    c.print(t)
    content = c.export_svg(title="报错のtraceback", code_format=CONSOLE_SVG_FORMAT)
    image = await html2img(
        content, {"device_scale_factor": 1.5}, {"type": "png", "full_page": True}
    )
    await send_debug(MessageChain(Image(data_bytes=image)))
