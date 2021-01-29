import json

path = 'ark_stages_info_all.json'
save_path = 'ark_stages_info.json'

with open(path, 'r', encoding='utf-8') as f:
    json_data = json.loads(f.read())

save_data = []
for i in json_data:
    save_data.append(
        {'stageId': i['stageId'],
         'name': i['code_i18n']['zh'],
         'apCost': i['apCost']
         }
    )

with open(save_path, 'w', encoding='utf-8') as f:
    f.write(json.dumps(save_data, indent=4))

print('over')