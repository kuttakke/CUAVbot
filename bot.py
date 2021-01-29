from graia.broadcast import Broadcast
import asyncio
from function.setu import SeTu
from function.search import FaShu, MoDu, SauceNAOSearch as SNS, SuKeBeNyaa as skb, WhatAnime as WA
from config.config import Config as cf
from graia.broadcast.builtin.decoraters import Depend
from function.judge import Judge
from function.baidu_search import u_can_baidu
from function.tenkafuma.tenka  import TenKaTool as TenKa
import graia.scheduler as scheduler
from graia.scheduler import timers
from function.timer_event.time_event import TimerEvent as TE
from function.timer_event.timer_for_crontabify import *
from function.dnd.roll_roulette_ import RollRoulette
from function.arktools.arks import ArkTools as Ark
from function.restart import Restart
from function.anime_timeline import get_anime_timeline
from graia.broadcast.interrupt import InterruptControl
from graia.application.interrupts import GroupMessageInterrupt, FriendMessageInterrupt
from graia.application.entry import (
    GraiaMiraiApplication,
    GroupMessage,
    At,
    Source,
    Image,
    MessageChain,
    Plain,
    Session,
    Friend,
    Group,
    Member,
)


config = cf().set_config()
help_str = cf().set_help()
dnd_help = cf().set_dnd_help()
fs_dict = FaShu.set_fashu()
ark_data = Ark.get_all_data()
tenka_op_list = TenKa.get_data()
setu = SeTu(config["lolicon_key"])
loop = asyncio.get_event_loop()
qq_numbers = config["qq"]
bcc = Broadcast(loop=loop)
roll = RollRoulette(qq_numbers["master"])
app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host=config["host"], # 填入 httpapi 服务运行的地址
        authKey=config["authKey"], # 填入 authKey
        account=config["account"], # 你的机器人的 qq 号
        websocket=True # Graia 已经可以根据所配置的消息接收的方式来保证消息接收部分的正常运作.
    )
)
inc = InterruptControl(bcc)
sche = scheduler.GraiaScheduler(loop=loop, broadcast=bcc)


@bcc.receiver("FriendMessage", headless_decoraters=[Depend(Judge.judge_help)])      # 好友 帮助
async def friend_message_listener(app: GraiaMiraiApplication, friend: Friend):
    out_msg = help_str
    await app.sendFriendMessage(friend, MessageChain.create([Plain(out_msg)]).asSendable())


@bcc.receiver("FriendMessage", headless_decoraters=[Depend(Judge.judge_md)])        # 好友 魔都搜索
async def friend_message_listener(app: GraiaMiraiApplication, message: MessageChain, friend: Friend):
    word = message.asDisplay()
    out_msg = MoDu.mozu(word)
    await app.sendFriendMessage(friend, MessageChain.create([Plain(out_msg)]).asSendable())


@bcc.receiver("FriendMessage", headless_decoraters=[Depend(Judge.judge_mf)])        # 好友 魔法查询
async def friend_message_listener(app: GraiaMiraiApplication, message: MessageChain, friend: Friend):
    word = message.asDisplay()
    res = FaShu.search_image_f(fs_dict, word)
    if res is None:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("无结果，请检查关键字")]).asSendable())
    else:
        await app.sendFriendMessage(friend, MessageChain.create([Image.fromLocalFile(res)]).asSendable())


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_help)])       # 群 帮助
async def group_message_handler(app: GraiaMiraiApplication, group: Group):
    out_msg = help_str
    await app.sendGroupMessage(group, MessageChain.create([Plain(out_msg)]).asSendable())


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_md)])     # 群 魔都查询
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group):
    word = message.asDisplay()
    out_msg = await MoDu.mozu(word)
    await app.sendGroupMessage(group, MessageChain.create([Plain(out_msg)]).asSendable())


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_mf)])     # 群 魔法查询
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group):
    word = message.asDisplay()
    res = FaShu.search_image_f(fs_dict, word)
    if res is None:
        await app.sendGroupMessage(group, MessageChain.create([Plain("无结果，请检查关键字")]).asSendable())
    else:
        await app.sendGroupMessage(group, MessageChain.create([Image.fromLocalFile(res)]).asSendable())


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_baidu)])      # 群 百度搜索
async def group_message_handler(app: GraiaMiraiApplication, message: MessageChain, group: Group):
    word = message.asDisplay()
    out_msg = u_can_baidu(word)
    await app.sendGroupMessage(group, MessageChain.create([Plain(out_msg)]).asSendable())



@sche.schedule(timers.crontabify(report_sleep))     # 赶紧睡觉！
async def send_sleep():
    path = TE.get_timer_img(1)
    await app.sendGroupMessage(qq_numbers["深夜剧场"], MessageChain.create(
        [Plain("早睡小助手提醒您：0点了！！"), Image.fromLocalFile(path)]).asSendable())
    await app.sendFriendMessage(qq_numbers["master"], MessageChain.create(
        [Plain("主人！早睡小助手提醒您：0点了！！"), Image.fromLocalFile(path)]).asSendable())


@sche.schedule(timers.crontabify(report_wake_up))       # 起床了！
async def send_wake_up():
    path = TE.get_timer_img(2)
    await app.sendGroupMessage(qq_numbers["深夜剧场"], MessageChain.create(
        [Plain("七点了..."), Image.fromLocalFile(path)]).asSendable())
    await app.sendFriendMessage(qq_numbers["master"], MessageChain.create(
        [Plain("七点了,主人早~"), Image.fromLocalFile(path)]).asSendable())


# ####################### ↓dnd相关


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_set_roll)])      # 群 设置轮盘
async def group_message_handler(app: GraiaMiraiApplication, member: Member, message: MessageChain, group: Group):
    kp = roll.get_kp()
    if kp == member.id:
        word = message.asDisplay()
        try:
            pl_num = int(word.replace(".dc", "").replace("。dc", "").strip())
        except:
            img_path = TE.get_timer_img(6)
            await app.sendGroupMessage(group, MessageChain.create(
                [Plain("好歹给个能用的数字啊kora"), Image.fromLocalFile(img_path)]).asSendable())
        else:
            if pl_num > 0:
                roll.set_roll(pl_num)
                await app.sendGroupMessage(group, MessageChain.create(
                    [Plain("弹仓容量设置为：{}人！".format(str(pl_num)))]).asSendable())
            else:
                await app.sendGroupMessage(group, MessageChain.create([Plain("人数必须比0大哦~")]).asSendable())
    else:
        img_path = TE.get_timer_img(4)
        await app.sendGroupMessage(group, MessageChain.create(
            [Plain("抱歉..你好像不是kp"), Image.fromLocalFile(img_path)]).asSendable())


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_pull_the_trigger)])       # 群 开枪
async def group_message_handler(app: GraiaMiraiApplication, member: Member, message: MessageChain, group: Group):
    kp = roll.get_kp()
    if kp == member.id:
        if message.has(At):
            aid = message.get(At)[0].target
            res = roll.pull_the_trigger()
            if res is False:
                await app.sendGroupMessage(group, MessageChain.create(
                    [At(aid), Plain("扣动了扳机...")]).asSendable())
                await asyncio.sleep(1)
                await app.sendGroupMessage(group, MessageChain.create([Plain("咔哒...")]).asSendable())
                await asyncio.sleep(1)
                await app.sendGroupMessage(group, MessageChain.create(
                    [Plain("没有子弹射出，"), At(aid), Plain("捡回了一条命")]).asSendable())
                await app.sendFriendMessage(kp, MessageChain.create(
                    [Plain("你指定了{}进行一次开枪： 空响".format(str(aid)))]))
            else:
                await app.sendGroupMessage(group, MessageChain.create(
                    [At(aid), Plain("扣动了扳机...")]).asSendable())
                await asyncio.sleep(1)
                await app.sendGroupMessage(group, MessageChain.create([Plain("咔哒...")]).asSendable())
                await asyncio.sleep(1)
                await app.sendGroupMessage(group, MessageChain.create(
                    [Plain("...BANG！！！"), At(aid), Plain("中弹身亡")]).asSendable())
                await app.sendFriendMessage(kp, MessageChain.create(
                    [Plain("你指定了{}进行一次开枪： 中弹".format(str(aid)))]))
        else:
            pass
    else:
        res = roll.pull_the_trigger()
        if res is False:
            await app.sendGroupMessage(group, MessageChain.create([
                At(member.id), Plain("扣动了扳机...")]).asSendable())
            await asyncio.sleep(1)
            await app.sendGroupMessage(group, MessageChain.create([Plain("咔哒...")]).asSendable())
            await asyncio.sleep(1)
            await app.sendGroupMessage(group, MessageChain.create(
                [Plain("没有子弹射出，"), At(member.id), Plain("捡回了一条命")]).asSendable())
            await app.sendFriendMessage(kp, MessageChain.create([Plain(member.name+"的结果是： 空响")]))
        else:
            await app.sendGroupMessage(group, MessageChain.create([
                At(member.id), Plain("扣动了扳机...")]).asSendable())
            await asyncio.sleep(1)
            await app.sendGroupMessage(group, MessageChain.create([Plain("咔哒...")]).asSendable())
            await asyncio.sleep(1)
            await app.sendGroupMessage(group, MessageChain.create(
                [Plain("...BANG！！！"), At(member.id), Plain("中弹身亡")]).asSendable())
            await app.sendFriendMessage(kp, MessageChain.create([Plain(member.name+"的结果是： 中弹")]))


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_set_kp)])         # 群 kp移交
async def group_message_handler(app: GraiaMiraiApplication, member: Member, group: Group):
    kp = roll.get_kp()
    if member.id == kp:
        await app.sendGroupMessage(group, MessageChain.create(
            [Plain("你不就就是kp来着"), Image.fromLocalFile(TE.get_timer_img(7))]))
    else:
        await app.sendGroupMessage(group, MessageChain.create(
            [Plain("kp权限即将移交给"), At(member.id), Plain('\n请输入"确认"来执行')]))
        await inc.wait(
            GroupMessageInterrupt(
                group, member,
                custom_judgement=lambda x: x.messageChain.asDisplay().startswith("确认"))
            )
        roll.set_kp(member.id)
        await app.sendGroupMessage(group, MessageChain.create(
            [Plain("你成为了kp！"), Image.fromLocalFile(TE.get_timer_img(8))]))


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_set_cheat_mod)])        # 私 开启上帝之手
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    fid = friend.id
    kp = roll.get_kp()
    if fid == kp:
        try:
            ct = int(message.asDisplay().replace(".sd", "").replace("。sd", "").strip())
        except:
            img_path = TE.get_timer_img(6)
            await app.sendFriendMessage(friend, MessageChain.create(
                [Plain("好歹给个能用的数字啊kora"), Image.fromLocalFile(img_path)]).asSendable())
        else:
            msg = roll.cheat_handler(True, cheat_times=ct)
            await app.sendFriendMessage(friend, MessageChain.create(
                [Plain(msg)]).asSendable())


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_stop_cheat_mod)])       # 私 关闭上帝之手
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    fid = friend.id
    kp = roll.get_kp()
    if fid == kp:
        msg = roll.cheat_handler()
        await app.sendFriendMessage(friend, MessageChain.create([Plain(msg)]).asSendable())


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_roll_get_now)])     # 私 得到目前轮盘情况
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    fid = friend.id
    kp = roll.get_kp()
    if fid == kp:
        msg = roll.get_now()
        await app.sendFriendMessage(friend, MessageChain.create([Plain(msg)]).asSendable())


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_reset_roll)])       # 私 重置
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend):
    kp = roll.get_kp()
    if friend.id == kp:
        msg = roll.reset()
        await app.sendFriendMessage(friend, MessageChain.create([Plain(msg)]))


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_dnd_help)])       # 群 dnd帮助
async def group_message_handler(app: GraiaMiraiApplication, group: Group, member: Member):
    await app.sendGroupMessage(group, MessageChain.create([Plain(dnd_help)]))


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_dnd_help)])     # 私 dnd帮助
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend):
    await app.sendFriendMessage(friend, MessageChain.create([Plain(dnd_help)]))


# ############  涩图 ###################


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_setu)])       # 群 涩图
async def group_message_handler(app: GraiaMiraiApplication, group: Group, message: MessageChain):
    word = message.asDisplay().replace(".涩图", "").replace("。涩图", "").strip()
    res = await setu.get_setu_with_keyword(False, word)
    if res is None:
        await app.sendGroupMessage(group, MessageChain.create([Plain("没有找到这个tag...")]))
    elif res is False:
        await app.sendGroupMessage(group, MessageChain.create([Plain("请求好像失败了QAQ")]))
    else:
        pid = "pid:" + res[0]
        out = res[1]
        await app.sendFriendMessage(qq_numbers['master'], MessageChain.create([Plain(pid), Image.fromUnsafeBytes(out)]))
        await app.sendGroupMessage(group, MessageChain.create([Plain(pid), Image.fromUnsafeBytes(out)]))


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_setu)])     # 私 涩图
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    word = message.asDisplay().replace(".涩图", "").replace("。涩图", "").strip()
    res = await setu.get_setu_with_keyword(True, word)
    if res is None:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("没有找到这个tag...")]))
    elif res is False:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("请求好像失败了QAQ")]))
    else:
        pid = "pid:" + res[0]
        out = res[1]
        await app.sendFriendMessage(friend, MessageChain.create([Plain(pid), Image.fromUnsafeBytes(out)]))


# ##################### 二次元搜图 #################


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_search_SauceNAO)])
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    if message.has(Image):
        i = message.get(Image)[0]
        msg = SNS.search_from_url(i.url)
        await app.sendFriendMessage(friend, MessageChain.create(msg))
    else:
        await app.sendFriendMessage(friend, MessageChain.create([
            Plain("请发送要搜索的图片")
        ]))
        f_even = await inc.wait(FriendMessageInterrupt(
            friend, custom_judgement=lambda x: x.messageChain.has(Image)
        ))
        i = f_even.messageChain.get(Image)[0]
        msg = SNS.search_from_url(i.url)
        await app.sendFriendMessage(friend, MessageChain.create(msg))


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_search_SauceNAO)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, member: Member, message: MessageChain):
    if message.has(Image):
        i = message.get(Image)[0]
        await app.sendGroupMessage(group, MessageChain.create([
            Plain("正在搜索....")
        ]))
        msg = SNS.search_from_url(i.url)
        msg.insert(0, At(member.id))
        msg.insert(1, Plain("\n"))
        await app.sendGroupMessage(group, MessageChain.create(msg))
    else:
        await app.sendGroupMessage(group, MessageChain.create([
            Plain("请发送要搜索的图片")
        ]))
        g_event = await inc.wait(GroupMessageInterrupt(
            group, member, custom_judgement=lambda x: x.messageChain.has(Image)
        ))
        await app.sendGroupMessage(group, MessageChain.create([
            Plain("正在搜索....")
        ]))
        i = g_event.messageChain.get(Image)[0]
        msg = SNS.search_from_url(i.url)
        msg.insert(0, At(member.id))
        msg.insert(1, Plain("\n"))
        await app.sendGroupMessage(group, MessageChain.create(msg))


# ################## 种子搜索 ##############


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_search_SuKeBe)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, member: Member, message: MessageChain):
    word = message.asDisplay().replace(".seed", "").replace("。seed", "").strip()
    if word:
        await app.sendGroupMessage(group, MessageChain.create([Plain("等等哈（翻找...")]))
        out_msg = await skb.get_res(word, True)
        out_msg.insert(0, At(member.id))
        out_msg.insert(1, Plain("\n"))
        await app.sendGroupMessage(group, MessageChain.create(out_msg))
    else:
        out_msg = [Plain("没有找到需要搜索的关键词...")]
        await app.sendGroupMessage(group, MessageChain.create(out_msg))


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_search_SuKeBe)])
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    word = message.asDisplay().replace(".seed", "").replace("。seed", "").strip()
    if word:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("等等哈（翻找...")]))
        out_msg = await skb.get_res(word)
        print(out_msg)
        await app.sendFriendMessage(friend, MessageChain.create(out_msg))
    else:
        out_msg = [Plain("没有找到需要搜索的关键词...")]
        await app.sendFriendMessage(friend, MessageChain.create(out_msg))


# ################ 使用what anime 进行搜番 ###########


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_search_Anime)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, member: Member, message: MessageChain):
    if message.has(Image):
        await app.sendGroupMessage(group, MessageChain.create([
            Plain("在找了....")
        ]))
        source = message.get(Image)[0]
        res = await WA.search_anime(source.url)
        res.append(At(member.id))
        await app.sendGroupMessage(group, MessageChain.create(res))
    else:
        await app.sendGroupMessage(group, MessageChain.create([Plain("请输入要搜索的番剧图片")]))
        g_event = await inc.wait(GroupMessageInterrupt(
            group, member, custom_judgement=lambda x: x.messageChain.has(Image)
        ))
        await app.sendGroupMessage(group, MessageChain.create([
            Plain("我找找....")
        ]))
        source = g_event.messageChain.get(Image)[0]
        res = await WA.search_anime(source.url)
        res.append(At(member.id))
        await app.sendGroupMessage(group, MessageChain.create(res))


@bcc.receiver("FriendMessage",  headless_decoraters=[Depend(Judge.judge_search_Anime)])
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend, message: MessageChain):
    if message.has(Image):
        await app.sendFriendMessage(friend, MessageChain.create([
            Plain("在找了....")
        ]))
        source = message.get(Image)[0]
        res = await WA.search_anime(source.url)
        await app.sendFriendMessage(friend, MessageChain.create(res))
    else:
        await app.sendFriendMessage(friend, MessageChain.create([Plain("请输入要搜索的番剧图片")]))
        g_event = await inc.wait(FriendMessageInterrupt(
            friend, custom_judgement=lambda x: x.messageChain.has(Image)
        ))
        await app.sendFriendMessage(friend, MessageChain.create([
            Plain("我找找....")
        ]))
        source = g_event.messageChain.get(Image)[0]
        res = await WA.search_anime(source.url)
        await app.sendFriendMessage(friend, MessageChain.create(res))


# ############ 舟 游 相 关 ###########


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_arktools_search_op)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, message: MessageChain):
    word = message.asDisplay().replace(".ark", "").replace("。ark", "").strip()
    out_msg = Ark.get_op(ark_data['op_data'], word)
    await app.sendGroupMessage(group, MessageChain.create(out_msg))


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_arktools_search_item)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, message: MessageChain):
    word = message.asDisplay().replace(".ari", "").replace("。ari", "").strip()
    out_msg = await Ark.search_ark_item(ark_data, word)
    await app.sendGroupMessage(group, MessageChain.create(out_msg))


# ############ 天 下 布 魔 #############


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_tenka_search_op)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, message: MessageChain):
    word = message.asDisplay().replace(".tenka", "").replace("。tenka", "").strip()
    out_msg = TenKa.get_tenka(tenka_op_list, word)
    await app.sendGroupMessage(group, MessageChain.create(out_msg))


# ############## 新 番 时 刻 表 ##########


@bcc.receiver("GroupMessage", headless_decoraters=[Depend(Judge.judge_anime_timeline)])
async def group_message_handler(app: GraiaMiraiApplication, group: Group, message: MessageChain):
    word = message.asDisplay().replace(".新番表", "").replace("。新番表", "").strip()
    res = await get_anime_timeline(word)
    await app.sendGroupMessage(group, MessageChain.create([Image.fromUnsafeBytes(res)]).asSendable())


# ###############  重 启 bot ##########


@bcc.receiver("FriendMessage", headless_decoraters=[Depend(Judge.judge_restart_all)])
async def friend_message_handler(app: GraiaMiraiApplication, friend: Friend):
    await app.sendFriendMessage(friend, MessageChain.create([Plain('bot即将重启，请输入yes进行确认')]))
    await inc.wait(
        FriendMessageInterrupt(
            friend, custom_judgement=lambda x: x.messageChain.asDisplay().startswith("yes"))
        )
    Restart.restart_program()






app.launch_blocking()
