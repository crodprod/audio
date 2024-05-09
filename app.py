import json
import logging
import os
import platform
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

import flet as ft
from apscheduler.triggers.cron import CronTrigger
from requests import get

from websockets.sync.client import connect
from dotenv import load_dotenv
from functions import load_config_file, update_config_file

load_dotenv()
go_find = False
ws_source = "ws://localhost:8010"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

ws = connect(ws_source, open_timeout=3, close_timeout=3)

def load_config():
    with open(file='config.json', mode='r', encoding='utf-8') as file:
        return json.load(file)


def get_yadisk_listdir(path: str = ""):
    url = f"https://cloud-api.yandex.net/v1/disk/resources?path=CROD_MEDIA/Общие файлы/Audio/{path}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f"OAuth {os.getenv('YANDEX_TOKEN')}"
    }
    response = get(url=url, headers=headers)
    if response.status_code == 200:
        return response.json()['_embedded']['items']
    else:
        return None


def send_data_to_ws(client: str, action: str, params=None):
    if params:
        params = str(params)
    data = {
        'client': client,
        'action': action,
        'params': params
    }
    print(data)
    ws.send(json.dumps(data))


def play_music():
    schedule = load_config()['schedule']
    for el in schedule:
        time = datetime.now().time()
        hour, minute = time.hour, time.minute
        if el['time']['hour'] == hour and el['time']['min'] == minute:
            for source in el['sources']:
                send_data_to_ws(source, 'play')


def stop_music():
    schedule = load_config()['schedule']
    for el in schedule:
        time = datetime.now().time()
        hour, minute = time.hour, time.minute
        if el['time']['hour'] == hour and el['time']['min'] == minute:
            for source in el['sources']:
                send_data_to_ws(source, 'pause')


scheduler = BackgroundScheduler()


def create_schedule():
    config = load_config()
    schedule = config['schedule']
    scheduler.remove_all_jobs()
    for index, el in enumerate(schedule):
        hour = el['time']['hour']
        minute = el['time']['min']
        action = el['action']

        if el['active']:
            if action == "play":
                job = scheduler.add_job(play_music, 'cron', hour=hour, minute=minute)
            elif action == "pause":
                job = scheduler.add_job(stop_music, 'cron', hour=hour, minute=minute)
            el['job_id'] = job.id
            schedule[index] = el

    config['schedule'] = schedule
    update_config_file(config)
    scheduler.start()
    scheduler.print_jobs()


def main(page: ft.Page):
    global go_find
    page.window_width = 377
    page.window_height = 768
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = ft.padding.only(left=10, right=10)
    page.theme = ft.Theme(
        font_family="Geologica",
        color_scheme=ft.ColorScheme(
            primary=ft.colors.WHITE
        )
    )
    page.fonts = {
        "Geologica": "fonts/Geologica.ttf",
    }

    page.appbar = ft.AppBar(
        title=ft.Text("Audio", size=20, weight=ft.FontWeight.W_400)
    )

    screens_data = {
        'audio_main': {
            'leading': None,
            'title': "Audio",
            'scroll': ft.ScrollMode.HIDDEN
        },
        'audio_settings': {
            'leading': ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: change_screen('audio_main'), tooltip="Назад"),
            'title': "Настройки",
            'scroll': ft.ScrollMode.HIDDEN
        },
        'audio_schedule': {
            'leading': ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: change_screen('audio_main'), tooltip="Назад"),
            'title': "Расписание",
            'scroll': ft.ScrollMode.HIDDEN
        },
        'pick_folder': {
            'leading': ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: change_screen('audio_main'), tooltip="Назад"),
            'title': "Выбор папки",
            'scroll': ft.ScrollMode.HIDDEN
        },
        'edit_timer': {
            'leading': ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: change_screen('audio_schedule'), tooltip="Назад"),
            'title': "Редактирование",
            'scroll': ft.ScrollMode.HIDDEN
        }
    }

    audio_appbar_actions = {
        'audio_main': [
            ft.Container(
                ft.Row(
                    [
                        ft.IconButton(ft.icons.UPDATE, on_click=lambda _: change_screen("audio_main")),
                        ft.ElevatedButton(icon=ft.icons.SCHEDULE, on_click=lambda _: change_screen('audio_schedule'), tooltip="Расписание", text="Расписание"),
                    ]
                ),
                margin=ft.margin.only(right=10)
            )
        ],
        'audio_settings': None,
        'audio_schedule': [
            ft.Container(
                ft.Row(
                    [
                        ft.IconButton(ft.icons.ADD_CIRCLE, on_click=lambda _: print("new"), tooltip="Добавить"),
                    ]
                ),
                margin=ft.margin.only(right=10)
            )
        ],
        'pick_folder': None,
        'edit_timer': None
    }

    new_clients = ft.Column()
    add_client_bottomsheet = ft.BottomSheet(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.Container(ft.Text("Добавление клиентов", size=20, weight=ft.FontWeight.W_500), expand=True),
                            ft.IconButton(ft.icons.CHECK_CIRCLE, on_click=lambda _: save_new_clients(), tooltip="Завершить")
                        ]
                    ),
                    ft.Column(
                        controls=[
                            ft.ProgressBar(),
                            ft.Text("Здесь будут появляться новые клиенты"),
                            new_clients,
                            # ft.Row(
                            #     [
                            #         ft.FilledTonalButton("Закончить", on_click=lambda _: save_new_clients()),
                            #     ],
                            #     alignment=ft.MainAxisAlignment.CENTER
                            # )

                        ]
                    )
                ]
            ),
            padding=15
        )
    )
    page.overlay.append(add_client_bottomsheet)

    # def goto_add_clients():
    #     global go_find
    #     go_find = True
    #     add_client_bottomsheet.open = True
    #     page.update()
    #     while go_find:
    #         ws = connect(ws_source)
    #         data = ws.recv()
    #         ws.close()
    #         print(data)
    #         data = json.loads(data)
    #         if data['action'] == "hello":
    #             saved_clients = load_config()['ws_clients']
    #             if data['client'] not in saved_clients:
    #                 new_clients.controls.append(ft.Text(data['client'], size=18, weight=ft.FontWeight.W_300))
    #                 time.sleep(1)
    #                 send_data_to_ws(data['client'], 'regok')
    #                 page.update()
    #             else:
    #                 send_data_to_ws(data['client'], 'errid')

    def change_audio_mode(e: ft.ControlEvent):
        mode = e.control.data
        page.controls.clear()
        if mode == 'single':
            page.add(all_card)
            card_single_mode.surface_tint_color = ft.colors.GREEN
            card_multi_mode.surface_tint_color = None
        elif mode == 'multi':
            change_screen("audio_main")
            card_single_mode.surface_tint_color = None
            card_multi_mode.surface_tint_color = ft.colors.GREEN
        page.update()

    card_single_mode = ft.Card(
        ft.Container(
            ft.Column(
                [
                    ft.ListTile(
                        title=ft.Text("Совмещённый", size=18, weight=ft.FontWeight.W_400),
                        subtitle=ft.Text("Все устройства играют один и тот же поток музыки", size=14, weight=ft.FontWeight.W_200),
                        leading=ft.Icon(ft.icons.SURROUND_SOUND),
                        data='single',
                        on_click=change_audio_mode
                    )
                ],
                # width=100,
                height=80
            ),
            padding=ft.padding.only(top=15, bottom=15)
        ),
        elevation=10
    )

    card_multi_mode = ft.Card(
        ft.Container(
            ft.Column(
                [
                    ft.ListTile(
                        title=ft.Text("Разделённый", size=18, weight=ft.FontWeight.W_400),
                        subtitle=ft.Text("Каждым устройством можно управлять отдельно", size=14, weight=ft.FontWeight.W_200),
                        leading=ft.Icon(ft.icons.FORMAT_LIST_NUMBERED),
                        data='multi',
                        on_click=change_audio_mode,
                        # disabled=True,
                    )
                ],
                # width=100,
                height=80
            ),
            padding=ft.padding.only(top=15, bottom=15)
        ),
        elevation=10,
        surface_tint_color=ft.colors.GREEN
    )

    mode_bottomsheet = ft.BottomSheet(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Режим работы", size=20, weight=ft.FontWeight.W_500),
                    ft.Column(
                        controls=[
                            card_single_mode,
                            card_multi_mode,
                        ]
                    )
                ]
            ),
            padding=15
        )
    )
    page.overlay.append(mode_bottomsheet)

    all_card = ft.Card(
        ft.Container(
            ft.Column(
                controls=[
                    ft.Row(
                        [
                            ft.Icon(ft.icons.MULTITRACK_AUDIO),
                            ft.Container(ft.Text('Общий', size=20, weight=ft.FontWeight.W_300), expand=True),
                            ft.IconButton(ft.icons.FOLDER_OPEN, data='all', on_click=lambda _: get_client_info('conference'))
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.IconButton(ft.icons.SKIP_PREVIOUS, icon_size=45, tooltip="Предыдущий трек", data=f"prevtrack_all", on_click=None),
                            ft.IconButton(ft.icons.PLAY_ARROW, icon_size=45, tooltip="Продолжить", visible=not True, data=f"play_all",
                                          on_click=None),
                            ft.IconButton(ft.icons.PAUSE, icon_size=45, tooltip="Пауза", data=f"pause_all", on_click=None, visible=True),
                            ft.IconButton(ft.icons.SKIP_NEXT, icon_size=45, tooltip="Следующий трек", data=f"nexttrack_all", on_click=None)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER
                    )
                ],
                # height=250,
                width=600
            ),
            # padding=15
            padding=15
        ),
        elevation=5
    )

    clients_list = ft.Column()

    def send_action(e: ft.ControlEvent):
        data = e.control.data.split("_")
        action, client, card_index = (data[0], data[1], int(data[2]))
        if action in ['play', 'pause', 'prevtrack', 'nexttrack']:
            response = send_data_to_ws(client, action)
        elif action == "setvolume":
            send_data_to_ws(client, action, int(e.control.value) / 100)

        page.update()

    def edit_timer(e: ft.ControlEvent):
        change_screen("edit_timer", e.control.data)

    def goto_pick_folder(e: ft.ControlEvent):
        change_screen("pick_folder", e.control.data)

    def change_screen(target: str, value=None):
        page.controls.clear()
        page.floating_action_button = None

        page.appbar.actions = audio_appbar_actions[target]
        page.appbar.leading = screens_data[target]['leading']
        page.appbar.title.value = screens_data[target]['title']
        page.scroll = screens_data[target]['scroll']

        clients = {
            # 0: {
            #     'name': 'sumstage',
            #     'title': 'Летняя сцена',
            #     'icon': ft.icons.SPEAKER
            # },
            # 1: {
            #     'name': 'territory',
            #     'title': 'Территория',
            #     'icon': ft.icons.TERRAIN
            # },
            2: {
                'name': 'conference',
                'title': 'Конференц-зал',
                'icon': ft.icons.CONTROL_CAMERA
            },
        }

        if target == "audio_main":
            clients_list.controls.clear()
            for index, c in enumerate(clients.items()):
                client = c[1]
                dialog_loading.content.controls[0].controls[0].value = f"Получение данных\n({client['title']})"
                open_dialog(dialog_loading)
                client_info = get_client_info(client['name'])
                # client_info = False
                print(client)
                if client_info is not False:
                    client_info = json.loads(client_info)

                    color = ft.colors.GREEN
                    vol_value = client_info['vol'] * 100
                    # btn_pause_visible = client_info['status']
                else:
                    color = ft.colors.RED
                    vol_value = 20
                    # btn_pause_visible = False

                client_card = ft.Card(
                    ft.Container(
                        ft.Column(
                            controls=[
                                ft.Row(
                                    [
                                        ft.Icon(client['icon'], color=color),
                                        ft.Container(ft.Text(client['title'], size=20, weight=ft.FontWeight.W_300), expand=True),
                                        ft.IconButton(ft.icons.FOLDER_OPEN, on_click=goto_pick_folder, data=client['name'])
                                    ]
                                ),
                                ft.Row(
                                    controls=[
                                        ft.IconButton(ft.icons.SKIP_PREVIOUS, icon_size=45, tooltip="Предыдущий трек", data=f"prevtrack_{client['name']}_{index}", on_click=send_action),
                                        ft.IconButton(ft.icons.PLAY_ARROW, icon_size=45, tooltip="Продолжить", data=f"play_{client['name']}_{index}",
                                                      on_click=send_action),
                                        ft.IconButton(ft.icons.PAUSE, icon_size=45, tooltip="Пауза", data=f"pause_{client['name']}_{index}", on_click=send_action),
                                        ft.IconButton(ft.icons.SKIP_NEXT, icon_size=45, tooltip="Следующий трек", data=f"nexttrack_{client['name']}_{index}", on_click=send_action)
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER
                                ),
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.icons.VOLUME_UP),
                                        ft.Container(
                                            ft.Slider(
                                                # min=0, max=100, divisions=20, label="{value}%", value=int(float(clients_info[index]['volume']) * 100), width=320, tooltip="Громкость",
                                                min=0, max=100, divisions=100, label="{value}%", value=vol_value, tooltip="Громкость",
                                                data=f"setvolume_{client['name']}_{index}",
                                                on_change_end=send_action,
                                                expand=True
                                            ),
                                            expand=True
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=0
                                )
                            ],
                            # height=250,
                            width=600
                        ),
                        # padding=15
                        padding=15
                    ),
                    elevation=5,
                    data=client['name']
                )
                clients_list.controls.append(client_card)
            close_dialog(dialog_loading)
            page.add(clients_list)

        elif target == "audio_schedule":
            config = load_config()
            schedule = config['schedule']

            action = {
                'play': {
                    'title': "Включение"
                },
                'pause': {
                    'title': "Выключние"
                }
            }

            sources = {
                'sumstage': "Летняя сцена",
                'conference': "КЗ",
                'territory': "Территория"
            }

            if len(schedule) > 0:
                col = ft.Column()
                for index, el in enumerate(schedule):
                    col.controls.append(
                        ft.Card(
                            ft.Container(
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    content=ft.ListTile(
                                                        title=ft.Text(f"{el['time']['hour']}:{el['time']['min']}", size=18, weight=ft.FontWeight.W_400),
                                                        subtitle=ft.Text(action[el['action']]['title'], size=18)
                                                    ),
                                                    expand=True,
                                                    padding=ft.padding.only(left=-15)
                                                ),
                                                ft.IconButton(ft.icons.EDIT, on_click=edit_timer, data=index),
                                                ft.IconButton(ft.icons.DELETE, ft.colors.RED, on_click=delete_timer, data=index),
                                                ft.Switch(value=el['active'], active_color=ft.colors.GREEN, on_change=change_timer_status, data=index)
                                            ]
                                        ),
                                        ft.Row(
                                            [
                                                ft.Icon(ft.icons.LOCATION_ON),
                                                ft.Text(', '.join([sources[index] for index in el['sources']]))
                                            ]
                                        )
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.START
                                ),
                                padding=15
                            ),
                            elevation=5
                        )
                    )
                page.add(col)
            else:
                page.add(ft.Text("Список расписания пуст", size=18, weight=ft.FontWeight.W_400))
        elif target == "audio_settings":
            pass
        elif target == "pick_folder":
            client_id = value
            loading_text.value = "Загрузка"
            open_dialog(dialog_loading)

            listdir = get_yadisk_listdir()

            if listdir is not None:
                col = ft.Column()
                listdir = [dir for dir in listdir if ".txt" not in dir['name']]
                for dir in listdir:
                    col.controls.append(
                        ft.Card(
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Container(ft.Text(dir['name'], size=18), expand=True),
                                        ft.IconButton(ft.icons.ARROW_FORWARD_IOS, on_click=send_new_path, data={'client_id': client_id, 'path': dir['name']})
                                    ]
                                ),
                                padding=ft.padding.only(left=15, right=15)
                            ),
                            elevation=5
                        )
                    )
                page.add(col)
            else:
                open_sb("Ошибка при получении данных", ft.colors.RED)
            close_dialog(dialog_loading)


        elif target == "edit_timer":
            config = load_config()
            schedule = config['schedule']
            cur_timer = schedule[value]

            for loc in cur_timer['sources']:
                for location in timer_locations.controls:
                    if loc == location.controls[0].data:
                        location.controls[0].value = True

            timer_action_dd.value = cur_timer['action']
            timer_time_btn.content.value = f"{cur_timer['time']['hour']}:{cur_timer['time']['min']}"
            # timer_datepicker.da

            col = ft.Column(
                [
                    ft.Card(
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text("Время", size=18, weight=ft.FontWeight.W_400), timer_time_btn
                                        ]
                                    )
                                ]
                            ),
                            padding=15
                        ),
                        elevation=5,
                        width=600
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Column(
                                        [
                                            ft.Text("Действие", size=18, weight=ft.FontWeight.W_400), timer_action_dd
                                        ]
                                    )
                                ]
                            ),
                            padding=15
                        ),
                        elevation=5,
                        width=600
                    ),
                    ft.Card(
                        ft.Container(
                            ft.Column(
                                [
                                    ft.Column(
                                        [
                                            ft.Text("Место", size=18, weight=ft.FontWeight.W_400), timer_locations
                                        ]
                                    )
                                ]
                            ),
                            padding=15
                        ),
                        elevation=5,
                        width=600
                    ),
                    ft.Row([ft.FilledTonalButton(text="Сохранить", icon=ft.icons.SAVE, on_click=update_timer, data=value)], alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.CENTER
            )

            page.add(col)

        page.update()

    def update_timer(e: ft.ControlEvent):
        timer_index = e.control.data
        config = load_config()
        schedule = config['schedule']
        cur_timer = schedule[timer_index]
        try:
            cur_timer['time']['hour'] = timer_datepicker.value.hour
            cur_timer['time']['min'] = timer_datepicker.value.minute
        except AttributeError:
            pass

        cur_timer['action'] = timer_action_dd.value

        sources = []
        for location in timer_locations.controls:
            if location.controls[0].value:
                sources.append(location.controls[0].data)
        cur_timer['sources'] = sources

        scheduler.remove_job(cur_timer['job_id'])
        if timer_action_dd.value == "play":
            job = scheduler.add_job(play_music, 'cron', hour=cur_timer['time']['hour'], minute=cur_timer['time']['min'])

        elif timer_action_dd.value == "pause":
            job = scheduler.add_job(stop_music, 'cron', hour=cur_timer['time']['hour'], minute=cur_timer['time']['min'])

        cur_timer['job_id'] = job.id
        scheduler.print_jobs()
        schedule[timer_index] = cur_timer
        config['schedule'] = schedule
        update_config_file(config)

        change_screen('audio_schedule')
        open_sb("Таймер сохранён", ft.colors.GREEN)

    def send_new_path(e: ft.ControlEvent):
        data = e.control.data
        client_id, path = data['client_id'], data['path']
        loading_text.value = "Отправка"
        open_dialog(dialog_loading)
        send_data_to_ws(
            client=client_id,
            action="setdir",
            params=path
        )
        close_dialog(dialog_loading)
        change_screen("audio_main")

    def datepicker_changed(e: ft.ControlEvent):
        time = e.control.value
        hour = "0" * (2 - len(str(time.hour))) + f"{time.hour}"
        minute = "0" * (2 - len(str(time.minute))) + f"{time.minute}"
        timer_time_btn.content.value = f"{hour}:{minute}"
        page.update()

    timer_datepicker = ft.TimePicker(
        time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY,
        cancel_text="Отмена",
        confirm_text="Сохранить",
        help_text='Выберите время срабатывания',
        on_change=datepicker_changed
    )
    page.overlay.append(timer_datepicker)

    timer_time_btn = ft.TextButton(on_click=lambda _: timer_datepicker.pick_time(), content=ft.Text(size=18))
    timer_action_dd = ft.Dropdown(
        options=[
            ft.dropdown.Option(text="Включить", key="play"),
            ft.dropdown.Option(text="Выключить", key="pause")
        ],
        hint_text="Выберите действие",
        width=200
    )
    timer_locations = ft.Column(
        [
            ft.Row(
                [
                    ft.Checkbox(data='sumstage'),
                    ft.Text("Летняя сцена")
                ]
            ),
            ft.Row(
                [
                    ft.Checkbox(data='territory'),
                    ft.Text("Территория")
                ]
            ),
            ft.Row(
                [
                    ft.Checkbox(data='conference'),
                    ft.Text("КЗ")
                ]
            )
        ]
    )

    def delete_timer(e: ft.ControlEvent):
        config = load_config_file()

        schedule = config['schedule']
        scheduler.remove_job(schedule[e.control.data]['job_id'])

        del schedule[e.control.data]
        update_config_file(config)

        open_sb("Таймер удалён")
        change_screen("audio_schedule")

    def change_timer_status(e: ft.ControlEvent):
        config = load_config_file()
        schedule = config['schedule']
        schedule[e.control.data]['active'] = e.control.value
        update_config_file(config)
        job_id = schedule[e.control.data]['job_id']
        if e.control.value:
            try:
                scheduler.resume_job(job_id)
            except Exception:
                job = scheduler.add_job(play_music, 'cron', hour=schedule[e.control.data]['time']['hour'], minute=schedule[e.control.data]['time']['min'])
                schedule[e.control.data]['job_id'] = job.id
                config['schedule'] = schedule
                update_config_file(config)

            current_time = datetime.now()
            target_time = datetime(current_time.year, current_time.month, current_time.day, schedule[e.control.data]['time']['hour'], schedule[e.control.data]['time']['min'])

            if target_time < current_time:
                target_time += timedelta(days=1)

            time_difference = target_time - current_time
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            time = ""
            if days != 0:
                time += f"{days} д."
            if hours != 0:
                time += f"{hours} ч. "
            if minutes != 0:
                time += f"{minutes} мин."

            open_sb(f"Таймер включен\nСработает через {time}", ft.colors.GREEN)
        else:
            scheduler.pause_job(job_id)

            open_sb("Таймер выключен")
        scheduler.print_jobs()

    def open_sb(text: str, bgcolor=ft.colors.WHITE):
        if bgcolor != ft.colors.WHITE:
            text_color = ft.colors.WHITE
        else:
            text_color = ft.colors.BLACK

        content = ft.Text(text, size=18, text_align=ft.TextAlign.START, weight=ft.FontWeight.W_300, color=text_color)
        page.snack_bar = ft.SnackBar(
            content=content,
            duration=1200,
            bgcolor=bgcolor
        )
        page.snack_bar.open = True
        page.update()

    def goto_audio_mode():
        mode_bottomsheet.open = True
        page.update()

    def get_client_info(client: str, params=None):
        data = {
            'client': client,
            'action': 'getinfo',
            'params': params
        }
        try:
            # ws = connect(ws_source, open_timeout=3, close_timeout=3)
            ws.send(json.dumps(data))

            try:
                fl = False
                while not fl:
                    msg = ws.recv(timeout=3)
                    data = json.loads(msg)
                    if data['client'] == client:
                        return json.loads(data['action'])
                    fl = True
                    # ws.close()
            except TimeoutError:
                open_sb(f"{client} недоступен ", ft.colors.RED)
                # ws.close()
                return False
            except Exception:
                # ws.close()
                return False

        except ConnectionRefusedError:
            open_sb("Веб-сокет недоступен", ft.colors.RED)
            return False

    loading_text = ft.Text("Загрузка", size=20, weight=ft.FontWeight.W_400)
    dialog_loading = ft.AlertDialog(
        # Диалог с кольцом загрузки

        # title=ft.Text(size=20),
        modal=True,
        content=ft.Column(
            controls=[
                ft.Column([loading_text, ft.ProgressBar()], alignment=ft.MainAxisAlignment.CENTER),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=400,
            height=50
        )
    )

    def open_dialog(dialog: ft.AlertDialog):
        page.dialog = dialog
        dialog.open = True
        page.update()

        if dialog == dialog_loading:
            # pass
            time.sleep(0.5)

    def close_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        page.update()

    def send_data_to_ws(client: str, action: str, params=None):
        if params:
            params = str(params)
        data = {
            'client': client,
            'action': action,
            'params': params
        }
        try:
            # ws = connect(ws_source, open_timeout=3, close_timeout=3)
            ws.send(json.dumps(data))
            # ws.close()
            return True
        except ConnectionRefusedError:
            open_sb("Веб-сокет недоступен", ft.colors.RED)
            return False

    change_screen('audio_main')


create_schedule()

if __name__ == '__main__':
    if platform.system() == "Windows":
        ft.app(
            target=main,
            assets_dir='assets',
            port=8502,
            view=ft.AppView.WEB_BROWSER
        )
    elif platform.system() == "Linux":
        ft.app(
            target=main,
            assets_dir='assets',
            name='',
            port=8502,
            view=None
        )
