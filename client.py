import datetime
import json
import logging
import os
import sys
import threading
import time
import ntplib

import websockets.exceptions

from colorama import init, Fore
from colorama import Back
from colorama import Style

from websockets.sync.client import connect

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from pygame import mixer

mixer.init()
init(autoreset=True)

ws_source = "wss://quick-reasonably-alien.ngrok-free.app"
# ws_source = "ws://localhost:8010"

pause = True
playlist = []
current_status = None
current_directory = r""
current_filename = ""

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


def color_text(text: str, bg: Back = "", textcol: Fore = Fore.BLACK, style: Style = ""):
    return bg + textcol + style + text + Style.RESET_ALL


print(color_text("ВЕБ-СОКЕТ", style=Style.BRIGHT, textcol=Fore.RESET))
connected = False
while not connected:
    try:
        print(color_text("Соединение с веб-сокетом...", Back.YELLOW))
        ws = connect(ws_source, open_timeout=3, close_timeout=3)
        print(color_text("Соединение с веб-сокетом установлено", Back.GREEN) + "\n")
        connected = True
    except Exception:
        print(color_text("Соединение не установлено. Следующая попытка через 5 секунд...", Back.RED) + "\n")
        time.sleep(5)


def sync_time():
    c = ntplib.NTPClient()
    response = c.request('pool.ntp.org')
    print(time.ctime(response.tx_time))


def autonext():
    global pause
    global current_filename
    global playlist
    while True:
        if not mixer.music.get_busy() and not pause:
            playlist = [el for el in os.listdir(current_directory) if el.endswith('.mp3')]
            for index, filename in enumerate(playlist):
                if filename == current_filename:
                    if index + 1 == len(playlist):
                        current_filename = playlist[0]
                    else:
                        current_filename = playlist[index + 1]
                    print(f"Следующий трек: {current_filename}")
                    ws_send(
                        message="nexttrack_answer",
                        body={
                            'status': 'ok',
                            'track': current_filename
                        }
                    )
                    mixer.music.load(os.path.join(current_directory, current_filename))
                    mixer.music.play()
                    break
        time.sleep(1)


auto_thread = threading.Thread(target=autonext)
auto_thread.start()


def ws_send(message: str, body: {}):
    data = {
        "sender": clients[int(client_id)]['id'],
        "recipient": "server",
        'message': message,
        'body': body
    }

    try:
        data = json.dumps(data)
        ws.send(data)
        print(f"<<< {data}")
    except ConnectionRefusedError:
        print("Веб-сокет недоступен")
        return False


def ws_recieve():
    try:
        data = ws.recv()
        return data
    except Exception:
        return False
    except TimeoutError:
        print("Клиент недоступен")
        return False
    except websockets.exceptions.ConnectionClosedOK:
        return False
    except websockets.exceptions.ConnectionClosedError:
        return False


def on_message_recieved(message: dict):
    global playlist
    global pause
    global global_last_volume  # храним в джейсоне
    global current_directory  # храним в джейсоне
    global current_filename

    action = message['message']
    data = message['body']

    if action == "setdir":
        playlist = []
        current_directory = f"{root_directory}\\{data['path']}"
        config = get_config()
        config['curdir'] = f"{root_directory}\\{data['path']}"
        update_config(config)
        print(f'Новая директория: {current_directory}')

        on_message_recieved({'message': 'nexttrack', 'body': {'track': data['file']}})

    elif action == "simplesync":
        delay = data['time'] - time.time()
        if delay > 0:
            time.sleep(delay)

        on_message_recieved(data)

    elif action == "getinfo":
        ws_send(
            message='getinfo_answer',
            body={
                'volume': mixer.music.get_volume(),
                'msuic_status': mixer.music.get_busy(),
                'current_dir': current_directory,
                'track': current_filename
            }
        )

    elif action == "pause":
        pause = True
        mixer.music.pause()
        print("Пауза")
        ws_send(
            message='pause_answer',
            body={
                'status': 'ok'
            }
        )

    elif action == "play":
        if current_directory:
            status = 'ok'
            pause = False
            mixer.music.unpause()
            print("Воспроизведение")
        else:
            status = 'empty_dir'
            print("Текущая директория отсутствует")

        ws_send(
            message='play_answer',
            body={
                'status': status,
                'track': current_filename,
                'msuic_status': mixer.music.get_busy()
            }
        )
    elif action == "setvolume":
        vol = data['volume']
        mixer.music.set_volume(float(vol))

        config = get_config()
        config['volume'] = float(vol)
        update_config(config)

        print(f"Установлена громкость: {float(vol) * 100}%")
        ws_send(
            message='setvolume_answer',
            body={
                'status': 'ok'
            }
        )

    elif action == "nexttrack":
        if current_directory:
            status = 'ok'
            if playlist:
                playlist = [el for el in os.listdir(current_directory) if el.endswith('.mp3')]
                for index, filename in enumerate(playlist):
                    if filename == current_filename:
                        if index + 1 == len(playlist):
                            current_filename = playlist[0]
                        else:
                            current_filename = playlist[index + 1]
                        print(f"Следующий трек: {current_filename}")
                        mixer.music.load(os.path.join(current_directory, current_filename))
                        mixer.music.play()
                        pause = False
                        break

            else:
                playlist = [el for el in os.listdir(current_directory) if el.endswith('.mp3')]
                if 'track' in data.keys() and data['track']:
                    current_filename = data['track']
                else:
                    current_filename = playlist[0]
                mixer.music.load(os.path.join(current_directory, current_filename))
                mixer.music.play()
                pause = False
        else:
            status = 'empty_dir'
            print("Текущая директория отсутствует")

        ws_send(
            message='nexttrack_answer',
            body={
                'status': status,
                'track': current_filename
            }
        )

    elif action == "prevtrack":
        if current_directory:
            status = 'ok'
            if playlist:
                playlist = [el for el in os.listdir(current_directory) if el.endswith('.mp3')]
                for index, filename in enumerate(playlist):
                    if filename == current_filename:
                        if index == 0:
                            current_filename = playlist[-1]
                        else:
                            current_filename = playlist[index - 1]
                        print(f"Предыдущий трек: {current_filename}")
                        mixer.music.load(os.path.join(current_directory, current_filename))
                        mixer.music.play()
                        pause = False
                        break
            else:
                playlist = [el for el in os.listdir(current_directory) if el.endswith('.mp3')]
                current_filename = playlist[0]
                mixer.music.load(os.path.join(current_directory, playlist[0]))
                mixer.music.play()
                pause = False
        else:
            status = 'empty_dir'
            print("Текущая директория отсутствует")

        ws_send(
            message='prevtrack_answer',
            body={
                'status': status,
                'track': current_filename
            }
        )

    else:
        print(f"Входящее сообщение не обработано: {message}")


def receive_messages():
    on_message_recieved({'message': 'getinfo', 'body': None})
    print("Клиент запущен. Ожидание команды от Audio...")
    global global_client_id
    while True:
        msg = ws_recieve()
        if msg is not False:
            data = json.loads(msg)
            if data['recipient'] == clients[int(client_id)]['id']:
                print(f">>> {data}")
                on_message_recieved(data)
        else:
            reboot()


data = {
    'client': 'conference',
    'action': 'getinfo',
    'params': None
}

clients = {
    1: {
        'title': 'Летняя сцена',
        'id': 'sumstage'
    },
    2: {
        'title': 'Территория',
        'id': 'territory'
    },
    3: {
        'title': 'Конференц-зал',
        'id': 'conference'
    }
}


def reboot():
    config = get_config()
    config['autorestart'] = True
    config['client_id'] = client_id
    update_config(config)
    os.execv(sys.executable, [sys.executable] + sys.argv)


def get_config():
    with open('audio_config/client_config.json', 'r') as f:
        return json.load(f)


def update_config(data):
    with open('audio_config/client_config.json', 'w') as f:
        return json.dump(data, f, ensure_ascii=False, indent=2)


print(color_text("КОНФИГУРАЦИЯ", style=Style.BRIGHT, textcol=Fore.RESET))
if not os.path.exists('audio_config'):
    print(color_text("Создание папки конфигурации", Back.YELLOW))
    os.mkdir('audio_config')

    with open('audio_config/client_config.json', 'w') as f:
        data = {
            "volume": 0,
            "rootdir": "",
            "curdir": "",
            "autorestart": False,
            "client_id": None
        }
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.close()
    print(color_text("Папка конфигурации создана", Back.GREEN) + "\n")
else:
    print(color_text("Папка конфигурации обнаружена", Back.GREEN) + "\n")

config = get_config()

print(color_text("ГРОМКОСТЬ", style=Style.BRIGHT, textcol=Fore.RESET))
if config['volume'] > 0:
    mixer.music.set_volume(config['volume'])
    print(color_text(f"Значение из конфигурации: {int(config['volume']) * 100}%", Back.GREEN) + "\n")
else:
    mixer.music.set_volume(0.5)
    config['volume'] = 0.5
    update_config(config)
    print(color_text("Стандартное значение: 50%", Back.GREEN) + "\n")

print(color_text("КОРНЕВАЯ ДИРЕКТОРИЯ", style=Style.BRIGHT, textcol=Fore.RESET))
if config['rootdir']:
    root_directory = config['rootdir']
    print(color_text(f"Значение из конфигурации: {config['rootdir']}", Back.GREEN) + "\n")
else:
    root_ok = False
    root_directory = input(color_text("Вставьте путь к папке \"CROD_MEDIA/Общие файлы/Audio\"", Back.YELLOW) + "\n>> ")
    while not root_ok:
        if os.path.exists(os.path.join(root_directory, 'checker.txt')):
            root_ok = True
        else:
            root_directory = input(color_text(f"Путь {root_directory} не является корректным, повторите попытку", Back.RED) + "\n>> ")
    config['rootdir'] = root_directory
    update_config(config)
    print(color_text(f"Директория установлена: {root_directory}", Back.GREEN) + "\n")

print(color_text("ТЕКУЩАЯ ДИРЕКТОРИЯ", style=Style.BRIGHT, textcol=Fore.RESET))
if config['curdir']:
    current_directory = config['curdir']
    print(color_text(f"Значение из конфигурации: {current_directory}", Back.GREEN) + "\n")
else:
    current_directory = ""
    print(color_text(f"Текущая директория отсутствует, выберите её в Audio", Back.CYAN) + "\n")

print("\nДля сброса параметров удалите папку audio_config")

if config['autorestart']:
    print("\n\nАвтоматическая перезагрузка из-за потери подключения к веб-сокету")
    client_id = config['client_id']
    config['autorestart'] = False
    update_config(config)
    on_message_recieved({'message': 'nexttrack', 'body': None})
else:
    client_id = input(
        "\nВведите ID клиента:"
        "\n1. Летняя сцена"
        "\n2. Территория"
        "\n3. Конференц-зал"
        "\n>> "
    )

    while client_id not in ['1', '2', '3']:
        print("Некорректные данные")
        client_id = input("Введите номер клиента"
                          "\n>> ")

print(f"Выбран клиент: {clients[int(client_id)]}")
# sync_time()
receive_messages()

ws.close()
