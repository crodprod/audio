import json
import threading
import time
import websocket

from pygame import mixer
from source.functions import update_config_file
import source.global_variables

mixer.init()


def control(action):
    file_path = ""
    print(f"CURRENT ACTION: {action}")
    with open("audio_config.json", mode="r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)

    if action in ['next', 'prev']:
        if action == "next":
            if config_data['current_track']['index'] + 1 == len(config_data['playlist']):
                file_path = config_data['playlist'][0]
                config_data['current_track']['index'] = 0
            else:
                file_path = config_data['playlist'][config_data['current_track']['index'] + 1]
                config_data['current_track']['index'] += 1
        elif action == "prev":
            if config_data['current_track']['index'] == 0:
                file_path = config_data['playlist'][len(config_data['playlist']) - 1]
                config_data['current_track']['index'] = len(config_data['playlist']) - 1
            else:
                file_path = config_data['playlist'][config_data['current_track']['index'] - 1]
                config_data['current_track']['index'] -= 1

        update_config_file(config_data)
        send_wss_data('/'.join(file_path.split("\\")[-2:]))
        # print('/'.join(file_path.split("\\")[-2:]))
        mixer.music.load(filename=file_path)
        mixer.music.play(fade_ms=1000)
        print(f"LOADED AND PLAYING: {file_path}")
    elif action == "pause":
        if source.global_variables.AUTOPLAY:
            source.global_variables.AUTOPLAY = False
        mixer.music.fadeout(1000)
        send_wss_data('pause')
        # mixer.music.load(config_data['current_track'])
        # time.sleep(10)
        # mixer.music.stop()
        print("PAUSED")
    elif action == "play":
        send_wss_data('play')
        mixer.music.unpause()
        print("RESUMED")

    if file_path:
        return file_path
    return None


def set_volume(volume_value: float):
    mixer.music.set_volume(volume_value)


def play_start_sound(sound_type: str):
    if sound_type == "start":
        mixer.music.load("start_sound.mp3")
    elif sound_type == "reboot":
        mixer.music.load("reboot_sound.mp3")
    mixer.music.play(fade_ms=1000)


def send_wss_data(data):
    try:
        ws = websocket.create_connection("wss://8c2c-31-134-188-48.ngrok-free.app/")
        ws.send(data)
        ws.close()
    except Exception as e:
        print("Ошибка при отправке данных:", e)


def auto_play():
    while True:
        if not mixer.music.get_busy() and source.global_variables.AUTOPLAY:
            control("next")
        else:
            # print(f"waiting to auto-play... {global_variables.AUTOPLAY}")
            time.sleep(1)


def start_music_check():
    music_check_thread = threading.Thread(target=auto_play)
    music_check_thread.start()
