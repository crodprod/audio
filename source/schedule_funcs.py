import threading
import multiprocessing
import time

import source.global_variables
from source.mixer_funcs import control, set_volume
from source.functions import load_config_file, update_config_file
from datetime import datetime


def main_schedule():
    print("schedule active")
    while True:
        current_date = datetime.now().date()
        current_time = datetime.now().time()
        config_data = load_config_file()
        schedule_list = config_data['schedule']
        for index, timer in enumerate(schedule_list):
            if timer['active'] and current_time.minute == int(timer['minutes']) and \
                    current_time.hour == int(timer['hours']) and str(current_date) != timer['last_action']:
                config_data['schedule'][index]['last_action'] = str(current_date)
                if timer['action'] == "next":
                    source.global_variables.AUTOPLAY = True
                    set_volume(timer['volume'] / 100)
                    config_data['volume'] = timer['volume']
                update_config_file(config_data)
                control(timer['action'])
        time.sleep(10)


def start_schedule():
    schedule_thread = threading.Thread(target=main_schedule)
    schedule_thread.start()
