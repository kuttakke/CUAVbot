from graia.application.entry import (
    MessageChain,
    Member,
    Friend
)
from config.config import Config as Cf
from graia.broadcast import ExecutionStop


class Judge:

    _master = Cf().set_config()['qq']["master"]     # 这样子很蠢，但是不想改了，懒

    @classmethod
    def __judge_setu(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".涩图") or word.startswith("。涩图"):
            return True

    @classmethod
    def __judge_mofa(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".mf") or word.startswith("。mf"):
            return True

    @classmethod
    def __judge_help(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".帮助") or word.startswith("。帮助"):
            return True

    @classmethod
    def __judge_modu(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".md") or word.startswith("。md"):
            return True

    @classmethod
    def __judge_baidu_serach(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".baidu") or word.startswith("。baidu"):
            return True

    # @classmethod
    # def __judge_is_kp(cls, member: Member, kp_id: int) -> bool:
    #     if member == kp_id:
    #         return True

    @classmethod
    def __judge_set_roll(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".dc") or word.startswith("。dc"):
            return True

    @classmethod
    def __judge_pull_the_trigger(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".kq") or word.startswith("。kq"):
            return True

    @classmethod
    def __judge_set_kp(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".ckp") or word.startswith("。ckp"):
            return True

    @classmethod
    def __judge_set_cheat_mod(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".sd") or word.startswith("。sd"):
            return True

    @classmethod
    def __judge_stop_cheat_mod(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".gsd") or word.startswith("。gsd"):
            return True

    @classmethod
    def __judge_roll_get_now(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".now") or word.startswith("。now"):
            return True

    @classmethod
    def __judge_dnd_help(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".dhelp") or word.startswith("。dhelp"):
            return True

    @classmethod
    def __judge_reset_roll(cls, msg: MessageChain) -> bool:
        word = msg.asDisplay().lower()
        if word.startswith(".czdc") or word.startswith("。czdc"):
            return True

    @classmethod
    def __judge_test(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith("test"):
            return True

    @classmethod
    def judge_setu(cls, msg: MessageChain):
        if not cls.__judge_setu(msg):
            raise ExecutionStop

    @classmethod
    def judge_mf(cls, msg: MessageChain):
        if not cls.__judge_mofa(msg):
            raise ExecutionStop

    @classmethod
    def judge_help(cls, msg: MessageChain):
        if not cls.__judge_help(msg):
            raise ExecutionStop

    @classmethod
    def judge_md(cls, msg: MessageChain):
        if not cls.__judge_modu(msg):
            raise ExecutionStop

    @classmethod
    def judge_baidu(cls, msg: MessageChain):
        if not cls.__judge_baidu_serach(msg):
            raise ExecutionStop

    # @classmethod
    # def judge_is_kp(cls, member: Member, kp_id: int):
    #     if not cls.__judge_is_kp(member, kp_id):
    #         raise ExecutionStop

    @classmethod
    def judge_set_roll(cls, msg: MessageChain):
        if not cls.__judge_set_roll(msg):
            raise ExecutionStop

    @classmethod
    def judge_pull_the_trigger(cls, msg: MessageChain):
        if not cls.__judge_pull_the_trigger(msg):
            raise ExecutionStop

    @classmethod
    def judge_set_kp(cls, msg: MessageChain):
        if not cls.__judge_set_kp(msg):
            raise ExecutionStop

    @classmethod
    def judge_set_cheat_mod(cls, msg: MessageChain):
        if not cls.__judge_set_cheat_mod(msg):
            raise ExecutionStop

    @classmethod
    def judge_stop_cheat_mod(cls, msg: MessageChain):
        if not cls.__judge_stop_cheat_mod(msg):
            raise ExecutionStop

    @classmethod
    def judge_roll_get_now(cls, msg: MessageChain):
        if not cls.__judge_roll_get_now(msg):
            raise ExecutionStop

    @classmethod
    def judge_dnd_help(cls, msg: MessageChain):
        if not cls.__judge_dnd_help(msg):
            raise ExecutionStop

    @classmethod
    def judge_reset_roll(cls, msg: MessageChain):
        if not cls.__judge_reset_roll(msg):
            raise ExecutionStop

    @classmethod
    def judge_test(cls, msg: MessageChain):
        if not cls.__judge_test(msg):
            raise ExecutionStop

    # ################## 这样写好累啊

    @classmethod
    def judge_search_SauceNAO(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".搜图") or word.startswith("。搜图"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_search_SuKeBe(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".seed") or word.startswith("。seed"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_search_Anime(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".搜番") or word.startswith("。搜番"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_arktools_search_op(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".ark") or word.startswith("。ark"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_tenka_search_op(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".tenka") or word.startswith("。tenka"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_arktools_search_item(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".ari") or word.startswith("。ari"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_anime_timeline(cls, msg: MessageChain):
        word = msg.asDisplay().lower()
        if word.startswith(".新番表") or word.startswith("。新番表"):
            return True
        else:
            raise ExecutionStop

    @classmethod
    def judge_restart_all(cls, friend: Friend, msg: MessageChain):
        if friend.id == cls._master:
            pass
        else:
            raise ExecutionStop
        word = msg.asDisplay().lower()
        if word.startswith(".restart") or word.startswith("。restart"):
            return True
        else:
            raise ExecutionStop
