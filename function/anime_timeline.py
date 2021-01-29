import aiohttp
from datetime import date, datetime
from PIL import Image as IMG
from PIL import ImageDraw, ImageFont
from io import BytesIO
import asyncio
from typing import Union, List
from graia.application.entry import Plain, Image
import aiofile


async def get_anime_timeline(time: str): # -> Union[List[Plain], List[Image]]
    today = int(datetime.fromisoformat(date.today().isoformat()).timestamp())
    date2ts = {'昨天': today-86400, '': today, '明天': today+86400}
    if time in date2ts:
        date_ts = date2ts[time]
    else:
        return [Plain('未知时间')]
    async with aiohttp.ClientSession() as session:
        async with session.get('https://bangumi.bilibili.com/web_api/timeline_global') as r:
            result = (await r.json())['result']
            data = next(anime_ts['seasons'] for anime_ts in result if anime_ts['date_ts'] == date_ts)
        final_back = IMG.new("RGB", (1200, 300 * len(data)), (40, 41, 35))
        final_draw = ImageDraw.Draw(final_back)
        for n, single in enumerate(data):
            async with session.get(single['square_cover']) as f:
                pic = IMG.open(BytesIO(await f.read()))
            if pic.size != (240, 240):
                pic = pic.resize((240, 240), IMG.ANTIALIAS)
            final_back.paste(pic, (30, 30 + 300 * n, 270, 270 + 300 * n))
            ttf = ImageFont.truetype('./function/ttf/simhei.ttf', 60)
            ellipsis_size = ttf.getsize('...')[0]
            if ttf.getsize(single['title'])[0] >= 900:
                while ttf.getsize(single['title'])[0] > 900 - ellipsis_size:
                    single['title'] = single['title'][:-1]
                single['title'] = single['title'] + '...'
            final_draw.text((300, 50 + 300 * n), single['title'], font=ttf, fill=(255, 255, 255))
            final_draw.text((300, 150 + 300 * n), single['pub_time'], font=ttf, fill=(255, 255, 255))
            final_draw.text((300 + ttf.getsize(single['pub_time'])[0] + 30, 150 + 300 * n),
                            single['pub_index'] if 'pub_index' in single else single['delay_index'] + single[
                                'delay_reason'],
                            font=ttf, fill=(0, 160, 216))
        print(type(final_back))
        out = BytesIO()
        final_back.save(out, format='JPEG')
        async with aiofile.async_open('anime.jpg', 'wb') as f:
            await f.write(out.getvalue())
        async with aiofile.async_open('anime.jpg', 'rb') as f:
            out_img = BytesIO(await f.read())
        return out_img.getvalue()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    tasks = [get_anime_timeline('明天')]
    return_value = loop.run_until_complete(asyncio.wait(tasks))
    print(return_value)
    loop.close()
