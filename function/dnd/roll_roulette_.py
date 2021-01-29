import random
import threading


class RollRoulette:

    def __init__(self, kp_id: int, pl_num: int = 6, cheat_mod: bool = False, cheat_times: int = -1):
        self._default = pl_num
        self._now_times = 1
        self._trigger = random.randint(1, pl_num)
        self._cheat_mod = cheat_mod
        self._cheat_times = cheat_times
        self._kp_id = kp_id
        self._lock = threading.RLock()

    def pull_the_trigger(self):
        self._lock.acquire()
        now_times = self._now_times
        trigger = self._trigger
        cheat_mod = self._cheat_mod
        cheat_times = self._cheat_times
        self._lock.release()
        if cheat_mod is True:
            if now_times == cheat_times:
                self.reset()
                return True
            else:
                self._lock.acquire()
                self._now_times += 1
                self._lock.release()
                return False
        else:
            if now_times == trigger:
                self.reset()
                return True
            else:
                self._lock.acquire()
                self._now_times += 1
                self._lock.release()
                return False

    def set_roll(self, pl_num: int = 6):
        self._lock.acquire()
        self._default = pl_num
        self._now_times = 1
        self._lock.release()

    def cheat_handler(self, cheat_mod: bool = False, cheat_times: int = -1):
        if cheat_mod is True:
            if cheat_times == -1:
                return "上帝之手需要传入指定次数！"
            elif 0 >= cheat_times > self._default:
                return "指定次数不能超过弹仓或低于等于0!"
            else:
                self._lock.acquire()
                self._cheat_mod = cheat_mod
                self._cheat_times = cheat_times
                self._lock.release()
                return "上帝之手开启，指定第{}次命中".format(str(cheat_times))
        else:
            self._lock.acquire()
            self._cheat_mod = cheat_mod
            self._lock.release()
            return "上帝之手关闭"

    def reset(self):
        self._lock.acquire()
        re = self._default
        self._now_times = 1
        self._trigger = random.randint(1, re)
        self._lock.release()
        print("重置成功")
        return "重置成功"

    def get_now(self):
        self._lock.acquire()
        msg = "人数：{}\n下一个是第{}个人开枪\n第{}个人会中枪\n上帝之手：{}-{}".format(self._default, self._now_times, self._trigger, self._cheat_mod, self._cheat_times)
        self._lock.release()
        return msg

    def get_kp(self):
        return self._kp_id

    def set_kp(self, id_: int):
        self._lock.acquire()
        self._kp_id = id_
        self._lock.release()




# if __name__ == '__main__':
#     r = RollRoulette()
#     it = [7, 9, 10, 12, 15]
#     for i in it:
#         if i == 9 or i == 12:
#             r.cheat_handler(True, 5)
#         else:
#             r.cheat_handler()
#         while True:
#             print("\n------------")
#             r.get_now()
#             if r.pull_the_trigger():
#                 print("中枪了！")
#                 r.set_roll(i)
#                 break
#             else:
#                 print("miss")
#             sleep(1)