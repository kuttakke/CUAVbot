from graia.application.message.chain import MessageChain
from graia.broadcast import ExecutionStop

class Function():

    @classmethod
    def jude(cls, message: MessageChain):
        mes = message.asDisplay()
        if mes.startswith(".") or mes.startswith("。"):
            return True

    @classmethod
    def judge_depend_target(cls, message: MessageChain):
        if not cls.jude(message):
            raise ExecutionStop()


    @classmethod
    def msg_handler(cls,msg:str):
        return msg.replace(".mf", "").strip()
        #return msg.replace(".mf", "").replace("。mf", "").strip()


