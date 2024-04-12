from json import dump, load


def update_config_file(data):
    with open("audio_config.json", mode="w", encoding="utf-8") as config_file:
        dump(data, config_file, indent=2)


def load_config_file():
    with open("audio_config.json", mode="r", encoding="utf-8") as config_file:
        data = load(config_file)
    # print(data)
    return data
