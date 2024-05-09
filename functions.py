from json import dump, load


def update_config_file(data):
    with open(file='config.json', mode="w", encoding="utf-8") as config_file:
        dump(data, config_file, indent=2, ensure_ascii=False)


def load_config_file():
    with open(file='config.json', mode="r", encoding="utf-8") as config_file:
        data = load(config_file)
    return data