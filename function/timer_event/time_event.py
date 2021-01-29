
class TimerEvent:
    _sleep_img_path = "./function/timer_event/image/快去睡觉.png"
    _wake_up_image_path = "./function/timer_event/image/早啊.png"
    _arknights_jiaomie = "./function/timer_event/image/提醒剿灭小助手.png"
    _sorry_path = "./function/timer_event/image/对不起啦.png"
    _lazy_guy_path = "./function/timer_event/image/大懒蛋.png"
    _anger_path = "./function/timer_event/image/生气.png"
    _question_path = "./function/timer_event/image/疑问.png"
    _wai_path = "./function/timer_event/image/哇咿.png"

    @classmethod
    def get_timer_img(cls, judge: int) -> str:
        """
        :param judge: 1-快去睡觉啊，2-早上好
        :return: 图片路径
        """
        if judge == 1:
            return cls._sleep_img_path
        elif judge == 2:
            return cls._wake_up_image_path
        elif judge == 3:
            return cls._arknights_jiaomie
        elif judge == 4:
            return cls._sorry_path
        elif judge == 5:
            return cls._lazy_guy_path
        elif judge == 6:
            return cls._anger_path
        elif judge == 7:
            return cls._question_path
        elif judge == 8:
            return cls._wai_path
