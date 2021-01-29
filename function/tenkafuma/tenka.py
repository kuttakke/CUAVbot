import json
from graia.application.entry import Plain


class TenKaTool:

    _test_path = 'tenka.json'
    _real_path = './function/tenkafuma/tenka.json'

    @classmethod
    def get_data(cls):
        with open(cls._real_path, "r", encoding='utf-8') as f:
            data = json.loads(f.read())["data"]
        return data

    @classmethod
    def get_tenka(cls, op_data: list, se_tag: str):
        want_tag = se_tag.split()
        len_tag = len(want_tag)
        if not want_tag:
            return [Plain("没有找到要搜索的tag...")]
        if len_tag == 1:
            res = cls._select(op_data, want_tag)
            return [Plain(res.strip())]
        elif len_tag <= 3:
            res = cls._select(op_data, want_tag)
            return [Plain(res.strip())]
        else:
            return [Plain("超过三个了...")]


    @classmethod
    def _select(cls, op_data: list, se_tag: list) -> str:
        out_msg_error = '好像没有任何结果，tag是不是输错了？...'
        if se_tag:
            limit = 2
            se_tag_len = len(se_tag)
            if se_tag_len == 1:
                tag_name = se_tag[0]
                res = cls._get_res_for_single_tag(op_data, tag_name)
                if res:
                    op_name = ''
                    for n in res:
                        op_name += n + " "
                        limit -= 1
                        if not limit:
                            limit = 2
                            op_name += '\n'
                    out_msg = tag_name + ':\n' + op_name
                    out_msg_ = out_msg.strip() + '\n'
                    return out_msg_
                else:
                    return out_msg_error
            elif se_tag_len == 2:
                tag_name = se_tag[0] + '+' + se_tag[1]
                res = cls._get_res_for_list_tag(op_data, se_tag)
                if res:
                    op_name = ''
                    for n in res:
                        op_name += n + " "
                        limit -= 1
                        if not limit:
                            limit = 2
                            op_name += '\n'
                    out_msg = tag_name + ':\n' + op_name
                    out_msg_ = out_msg.strip() + '\n'
                    return out_msg_
                else:
                    return out_msg_error
            elif se_tag_len == 3:
                res_list = []
                for i in range(se_tag_len - 1):
                    res = cls._get_res_for_list_tag(op_data, [se_tag[i], se_tag[i+1]])
                    if res:
                        limit = 2
                        tag_name = se_tag[i] + '+' + se_tag[i+1]
                        op_name = ''
                        for n in res:
                            op_name += n + " "
                            limit -= 1
                            if not limit:
                                limit = 2
                                op_name += '\n'
                        msg = tag_name + ':\n' + op_name + '\n'
                        out_msg_ = msg.strip() + '\n'
                        res_list.append(out_msg_)
                res_1_3 = cls._get_res_for_list_tag(op_data, [se_tag[0], se_tag[2]])
                if res_1_3:
                    tag_name = se_tag[0] + '+' + se_tag[2]
                    op_name = ''
                    for n in res_1_3:
                        op_name += n + " "
                        limit -= 1
                        if not limit:
                            limit = 2
                            op_name += '\n'
                    msg = tag_name + ':\n' + op_name + '\n'
                    out_msg_ = msg.strip() + '\n'
                    res_list.append(out_msg_)
                res_all = cls._get_res_for_list_tag(op_data, se_tag)
                if res_all:
                    tag_name = se_tag[0] + '+' + se_tag[1] + '+' + se_tag[2]
                    op_name = ''
                    for n in res_all:
                        op_name += n + " "
                    msg = tag_name + ':\n' + op_name + '\n'
                    out_msg_ = msg.strip() + '\n'
                    res_list.append(out_msg_)
                if res_list:
                    msg_all = ''
                    for i in res_list:
                        msg_all += i
                    return msg_all
                else:
                    return out_msg_error
        else:
            return out_msg_error

    @classmethod
    def _get_res_for_single_tag(cls, op_data: list, se_tag: str):
        res = []
        for op in op_data:
            if se_tag in op:
                res.append(op[0])
        return res

    @classmethod
    def _get_res_for_list_tag(cls, op_data: list, se_tag: list):
        res = []
        tag_len = len(se_tag)
        if tag_len == 2:
            for op in op_data:
                if all([
                    se_tag[0] in op, se_tag[1] in op
                ]):
                    res.append(op[0])
        else:
            for op in op_data:
                if all([
                    se_tag[0] in op, se_tag[1] in op, se_tag[2] in op
                ]):
                    res.append(op[0])

        return res




if __name__ == '__main__':
    tenka = TenKaTool
    op = tenka.get_data()
    tag = '妨碍者 魔族'
    msg = tenka.get_tenka(op, tag)
    print(msg)
