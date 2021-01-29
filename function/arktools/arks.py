import json
from typing import Union
from graia.application.entry import Plain
from typing import List
import aiohttp
import asyncio


class ArkTools:

    _Penguin_api_base_url = 'https://penguin-stats.io/PenguinStats'
    _Penguin_item = '/api/v2/result/matrix'
    _test_path = "akhr.json"
    _ob_path = './function/arktools/akhr.json'
    _test_item_path = './function/arktools/ark_items.json'
    _ark_formula_path = './function/arktools/ark_formula.json'
    _ark_stages_path = './function/arktools/ark_stages_info.json'


    @classmethod
    def get_data(cls) -> list:
        with open(cls._ob_path, 'rb') as f:
            data_ = json.loads(f.read())
        return data_

    @classmethod
    def _select(cls, op_data: list, se_tag: Union[list, str]) -> str:
        res = []
        if isinstance(se_tag, list):
            for i in se_tag:
                res_op = cls._get_res_for_single_tag(op_data, i)
                if res_op[1]:
                    tag_name = i + ":" + '\n'
                    res_p = tag_name + res_op[1] + '\n'
                    res.append([res_op[0], res_p])
            tag_len = len(se_tag)
            for i in range(tag_len - 1):
                tag_list = [se_tag[i], se_tag[i+1]]
                res_op = cls._get_res_for_list_tag(op_data, tag_list)
                if res_op[1]:
                    tag_name = se_tag[i] + "+" + se_tag[i+1] + ":" + '\n'
                    res_p = tag_name + res_op[1] + '\n'
                    res.append([res_op[0], res_p])
            if tag_len == 3:
                res_1_to_3 = cls._get_res_for_list_tag(op_data, [se_tag[0], se_tag[2]])
                if res_1_to_3[1]:
                    tag_name = se_tag[0] + "+" + se_tag[2] + ":" + '\n'
                    res_p = tag_name + res_1_to_3[1] + '\n'
                    res.append([res_1_to_3[0], res_p])
                res_op = cls._get_res_for_list_tag(op_data, se_tag)
                if res_op[1]:
                    tag_name = se_tag[0] + "+" + se_tag[1] + "+" + se_tag[2] + ":" + '\n'
                    res_p = tag_name + res_op[1] + '\n'
                    res.append([res_op[0], res_p])
        elif isinstance(se_tag, str):
            res_op = cls._get_res_for_single_tag(op_data, se_tag)
            if res_op[1]:
                tag_name = se_tag + ":" + '\n'
                res_p = tag_name + res_op[1] + '\n'
                res.append([res_op[0], res_p])
        tar = any(
            i[0] for i in res
        )
        multiple_combinations = any(
            "+" in i[1] for i in res
        )
        out_str = ''
        if tar:
            for op in res:
                if op[0]:
                    out_str += op[1]
        else:
            if multiple_combinations:
                for op in res:
                    if "+" in op[1]:
                        out_str += op[1]
        return out_str

    @classmethod
    def get_op(cls, op_data: list, se_tag: str) -> Union[List[Plain]]:
        want_tag = se_tag.split()
        len_tag = len(want_tag)
        if not want_tag:
            return [Plain("没有找到要搜索的tag...")]
        if len_tag == 1:
            res = cls._select(op_data, want_tag[0])
            if res:
                return [Plain(res.strip())]
            else:
                return [Plain("好像没有任何结果，tag是不是输错了？...")]
        elif len_tag <= 3:
            res = cls._select(op_data, want_tag)
            if res:
                return [Plain(res.strip())]
            else:
                return [Plain("好像没有任何结果，tag是不是输错了？...")]
        else:
            return [Plain("超过三个了...")]

    @classmethod
    def _get_res_for_single_tag(cls, op_data: list, se_tag: str):
        res = []
        if se_tag == "高级资深干员":
            trigger = True
        else:
            trigger = False
        for op in op_data:
            op_tag = op["tags"]
            op_type = op["type"]
            if se_tag in op_tag or se_tag == op_type:
                res.append([op["name"], op["level"]])
        return cls._sort_for_op(res, trigger)

    @classmethod
    def _get_res_for_list_tag(cls, op_data: list, se_tag: list):
        res = []
        if "高级资深干员" in se_tag:
            trigger = True
        else:
            trigger = False
        tag_len = len(se_tag)
        if tag_len == 2:
            for op in op_data:
                op_tag = op["tags"]
                op_type = op["type"]
                if any(
                    [se_tag[0] in op_tag,
                     se_tag[0] == op_type]
                ) and any(
                    [se_tag[1] in op_tag,
                     se_tag[1] == op_type]
                ):
                    res.append([op["name"], op["level"]])
        else:
            for op in op_data:
                op_tag = op["tags"]
                op_type = op["type"]
                if any(
                        [se_tag[0] in op_tag,
                         se_tag[0] == op_type]
                ) and any(
                    [se_tag[1] in op_tag,
                     se_tag[1] == op_type]
                ) and any(
                    [se_tag[2] in op_tag,
                     se_tag[2] == op_type]
                ):
                    res.append([op["name"], op["level"]])
        return cls._sort_for_op(res, trigger)

    @classmethod
    def _sort_for_op(cls, sel_res: list, senior: bool = False):
        if sel_res:
            op_star = [[], [], [], [], []]
            is_op_have_3_star = False
            for op in sel_res:
                op_name = op[0]
                op_level = op[1]
                if op_level == 3:
                    is_op_have_3_star = True
                    op_star[1].append(str(op_level) + '*' + op_name)
                elif op_level == 4:
                    op_star[2].append(str(op_level) + '*' + op_name)
                elif op_level == 5:
                    op_star[3].append(str(op_level) + '*' + op_name)
                elif op_level == 6 and senior:
                    op_star[4].append(str(op_level) + '*' + op_name)
                elif op_level == 1:
                    op_star[0].append(str(op_level) + '*' + op_name)
            if is_op_have_3_star:
                out = '可赌：'
                final_list = [op_star[2], op_star[3]]
                for op in final_list:
                    if op:
                        lim = 0
                        line_lim = 0
                        for i in op:
                            if lim >= 3:
                                break
                            out += i+" "
                            lim += 1
                            line_lim += 1
                            if line_lim >= 3:
                                out += '\n\u3000'
                                line_lim = 0
                out = out.strip() + '\n'
                return [0, out]
            else:
                out = '高价值目标：'
                final_list = [op_star[0], op_star[2], op_star[3], op_star[4]]
                for op in final_list:
                    if op:
                        line_lim = 0
                        for i in op:
                            out += i+" "
                            line_lim += 1
                            if line_lim >= 3:
                                out += '\n\u3000'
                                line_lim = 0
                out = out.strip() + '\n'
                return [1, out]
        else:
            return [0, None]

    @classmethod
    def get_all_data(cls):
        '''
        :return: 拿到所有ark数据
        '''
        items_path = cls._test_item_path
        formula_path = cls._ark_formula_path
        stages_path = cls._ark_stages_path
        with open(cls._ob_path, 'rb') as f:
            op_data = json.loads(f.read())
        with open(items_path, 'r', encoding='utf-8') as f:
            items_data = json.loads(f.read())
        with open(formula_path, 'r', encoding='utf-8') as f:
            formula_data = json.loads(f.read())
        with open(stages_path, 'r',encoding='utf-8') as f:
            stages_data = json.loads(f.read())
        data = {
            'op_data': op_data,
            'items_data': items_data,
            'formula_data': formula_data,
            'stages_data': stages_data
        }
        return data

    @classmethod
    def get_all_data_test(cls):
        '''
        :return: 拿到所有ark数据
        '''
        op_path = "akhr.json"
        items_path = 'ark_items.json'
        formula_path = "ark_formula.json"
        stages_path = "ark_stages_info.json"
        with open(op_path, 'rb') as f:
            op_data = json.loads(f.read())
        with open(items_path, 'r', encoding='utf-8') as f:
            items_data = json.loads(f.read())
        with open(formula_path, 'r', encoding='utf-8') as f:
            formula_data = json.loads(f.read())
        with open(stages_path, 'r',encoding='utf-8') as f:
            stages_data = json.loads(f.read())
        data = {
            'op_data': op_data,
            'items_data': items_data,
            'formula_data': formula_data,
            'stages_data': stages_data
        }
        return data

    @classmethod
    async def search_ark_item(cls, data, item_name: str) -> Union[List[Plain]]:
        if item_name:
            for item in data['items_data']:
                names = item['alias']['zh']
                for name in names:
                    if item_name == name:
                        return [Plain(await cls._search_item(
                            data['formula_data'], data['stages_data'], item['itemId'], item_name
                        ))]
                    else:
                        return [Plain('好像没有这个素材QAQ')]


    @classmethod
    async def _search_item(cls, formula_data, stages_data, item_key: str, item_name) -> str:
        out_list = []
        items = cls._items_ex_handler(formula_data, item_key, item_name)
        for item_ in items:
            item = item_[0]
            params_ = {'itemFilter': item}
            url = cls._Penguin_api_base_url + cls._Penguin_item
            async with aiohttp.request('GET', url, params=params_) as res_url:
                if res_url.status == 200:
                    result_name = []
                    result_possibility = []
                    all_items_matrix = await res_url.json()
                    for i in all_items_matrix['matrix']:
                        result_name.append(i['stageId'])
                        result_possibility.append(i['quantity'] / i['times'])
                    item_max = max(result_possibility)
                    index_for_max_va = result_possibility.index(item_max)
                    item_name_and_cost = cls._from_id_get_name_and_cost(stages_data, result_name)
                    len_result = len(result_possibility)
                    result_cost = []
                    for i in range(len_result):
                        if result_possibility[i] != 0:
                            result_cost.append(item_name_and_cost[i][1] / result_possibility[i])
                        else:
                            result_cost.append(100)
                    result_most_less_cost = min(result_cost)
                    index_for_min_cost = result_cost.index(result_most_less_cost)
                    str_start = item_[1] + "\n"

                    str_max = '价值最高图[' + item_name_and_cost[index_for_max_va][0] + ']： ' + ("%.2f%%" % (item_max * 100)) + "\n"
                    str_min = 'cost最低图[' + item_name_and_cost[index_for_min_cost][0] + "]： " + ("%.2f" % result_most_less_cost) + "\n"
                    str_ = str_start + str_max + str_min
                    out_list.append(str_)
                else:
                    print("error")
        if out_list and all([i for i in out_list]):
            out_str = ''
            for out in out_list:
                out_str += out
            return out_str.strip()
        else:
            return '好像没有结果QAQ...'

    @classmethod
    def _items_ex_handler(cls, formula_data, item_id: str, item_name: str) -> list:       # 这里拿到此材料的子材料
        need_to_get_res_item = [[item_id, item_name], ]
        for item in formula_data:
            if item['id'] == item_id:
                for i in item['costs']:
                    need_to_get_res_item.append([i['id'], i['name']])
                return need_to_get_res_item
        return need_to_get_res_item

    @classmethod
    def _from_id_get_name_and_cost(cls, data: list, items_id: Union[list, str]) -> list:        # 以id找到场地名字
        if isinstance(items_id, list):
            all_result = []
            for item_data in items_id:
                for i in data:
                    if i['stageId'] == item_data:
                        all_result.append([i['name'], i['apCost']])
            return all_result


if __name__ == '__main__':

    ark = ArkTools
    # data = ark.get_data()
    # tag = '削弱 输出 费用回复'
    # list_ = ark.get_op(data, tag)
    # print(list_)
    # ark.search_item(30104)
    d = ark.get_all_data_test()
    name = '改良装置'
    loop = asyncio.get_event_loop()
    tasks = [ark.search_ark_item(d, name)]
    res = loop.run_until_complete(asyncio.wait(tasks))
    # res = ark.search_ark_item(d, name)
    print(res)
    print(type(res))
