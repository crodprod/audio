import json
import logging
import os
import platform
import time
import flet as ft

from requests import get
from dotenv import load_dotenv
from datetime import datetime, timedelta
from websockets.sync.client import connect
from apscheduler.schedulers.background import BackgroundScheduler

from elements.screens import screens_data

load_dotenv()

ws_status = {'status': False, 'error': ""}
ws_source = "wss://quick-reasonably-alien.ngrok-free.app"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

os.environ['FLET_WEB_APP_PATH'] = '/audio'

try:
    ws = connect(ws_source, open_timeout=3, close_timeout=3)
    ws_status['status'] = True
except Exception as e:
    ws_status['status'] = False
    ws_status['error'] = e
scheduler = BackgroundScheduler()


def load_config():
    with open(file='config.json', mode='r', encoding='utf-8') as file:
        return json.load(file)


def update_config(data):
    with open(file='config.json', mode="w", encoding="utf-8") as config_file:
        json.dump(data, config_file, indent=2, ensure_ascii=False)


def get_yadisk_listdir(path: str = ""):
    url = f"https://cloud-api.yandex.net/v1/disk/resources"

    headers = {
        'Accept': 'application/json',
        'Authorization': f"OAuth {os.getenv('YANDEX_TOKEN')}"
    }

    params = {
        'path': f"CROD_MEDIA/Общие файлы/Audio/{path}"
    }

    response = get(url=url, headers=headers, params=params)

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
    ws.send(json.dumps(data))


def play_music():
    schedule = load_config()['schedule']
    for el in schedule:
        time = datetime.now().time()
        hour, minute = time.hour, time.minute
        if el['time']['hour'] == hour and el['time']['min'] == minute:
            for source in el['sources']:
                send_data_to_ws(source, 'nexttrack')


def stop_music():
    schedule = load_config()['schedule']
    for el in schedule:
        time = datetime.now().time()
        hour, minute = time.hour, time.minute
        if el['time']['hour'] == hour and el['time']['min'] == minute:
            for source in el['sources']:
                send_data_to_ws(source, 'pause')


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
    update_config(config)

    scheduler.start()
    scheduler.print_jobs()


def main(page: ft.Page):
    if platform.system() == "Windows":
        page.window_width = 377
        page.window_height = 768

    page.title = "Audio"

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
        title=ft.Text("Audio", size=20, weight=ft.FontWeight.W_400),
    )

    def login():
        true_password = os.getenv('ACCESS_CODE')
        if login_field.value == true_password:
            change_screen("main")
        else:
            open_sb("Неверный код")
        login_field.value = ""
        page.update()

    def goto_pick_folder(e: ft.ControlEvent):
        change_screen("pick_folder", e.control.data)

    audio_appbar_actions = {
        'login': None,
        'main': [
            ft.Container(
                ft.Row(
                    [
                        ft.IconButton(ft.icons.MULTITRACK_AUDIO, on_click=goto_pick_folder, data='all', tooltip="Синхронизация"),
                        ft.IconButton(ft.icons.UPDATE, on_click=lambda _: change_screen("main"), tooltip="Обновить"),
                        ft.IconButton(icon=ft.icons.SCHEDULE, on_click=lambda _: change_screen('schedule'), tooltip="Расписание"),
                    ]
                ),
                margin=ft.margin.only(right=10)
            )
        ],
        'settings': None,
        'schedule': [
            ft.Container(
                ft.Row(
                    [
                        ft.IconButton(ft.icons.ADD_CIRCLE, on_click=lambda _: change_screen("new_timer"), tooltip="Новый таймер"),
                    ]
                ),
                margin=ft.margin.only(right=10)
            )
        ],
        'pick_folder': None,
        'edit_timer': None,
        'new_timer': None
    }

    def send_action(e: ft.ControlEvent):
        data = e.control.data.split("_")
        action, client, card_index = (data[0], data[1], int(data[2]))
        if action in ['play', 'pause', 'prevtrack', 'nexttrack']:
            response = send_data_to_ws(client, action)
        elif action == "setvolume":
            send_data_to_ws(client, action, int(e.control.value) / 100)

        page.update()

    def change_screen(target: str, value=None):
        page.controls.clear()
        page.floating_action_button = None
        page.appbar.visible = True

        page.appbar.actions = audio_appbar_actions[target]
        if screens_data[target]['leading']['icon'] is not None:
            page.appbar.leading = ft.IconButton(screens_data[target]['leading']['icon'], on_click=lambda _: change_screen(screens_data[target]['leading']['target']))
        page.appbar.title.value = screens_data[target]['title']
        page.scroll = screens_data[target]['scroll']

        clients = {
            0: {
                'name': 'sumstage',
                'title': 'Летняя сцена',
                'icon': ft.icons.SPEAKER
            },
            1: {
                'name': 'territory',
                'title': 'Территория',
                'icon': ft.icons.TERRAIN
            },
            2: {
                'name': 'conference',
                'title': 'Конференц-зал',
                'icon': ft.icons.CONTROL_CAMERA
            },
        }

        if target == "login":
            page.appbar.visible = False
            page.add(ft.Container(login_col, expand=True))

        elif target == "main":
            clients_list = ft.Column()
            for index, c in enumerate(clients.items()):
                client = c[1]
                dialog_loading.content.controls[0].controls[0].value = f"Получение данных\n({client['title']})"
                open_dialog(dialog_loading)
                client_info = get_client_info(client['name'])
                # client_info = False
                # print(client)
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

        elif target == "schedule":
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
                    h, m = "0" * (2 - len(str(el['time']['hour']))) + f"{el['time']['hour']}", "0" * (2 - len(str(el['time']['min']))) + f"{el['time']['min']}"
                    col.controls.append(
                        ft.Card(
                            ft.Container(
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Container(
                                                    content=ft.ListTile(
                                                        title=ft.Text(f"{h}:{m}", size=18, weight=ft.FontWeight.W_400),
                                                        subtitle=ft.Text(action[el['action']]['title'], size=18)
                                                    ),
                                                    expand=True,
                                                    padding=ft.padding.only(left=-15)
                                                ),
                                                ft.PopupMenuButton(
                                                    items=[
                                                        ft.FilledButton(text='Редактировать', icon=ft.icons.EDIT, on_click=goto_edittimer, data=index),
                                                        ft.Divider(thickness=1),
                                                        ft.FilledButton(text='Удалить', icon=ft.icons.DELETE, on_click=delete_timer, data=index),
                                                    ]
                                                ),
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
                            elevation=5,
                            width=600
                        )
                    )
                page.add(col)
            else:
                page.add(ft.Text("Список расписания пуст", size=18, weight=ft.FontWeight.W_400))
        elif target == "settings":
            pass
        elif target == "pick_folder":
            client_id = value
            loading_text.value = "Загрузка"
            open_dialog(dialog_loading)

            listdir = get_yadisk_listdir()

            if listdir is not None:
                col = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                col.controls.append(ft.Text('Выберите папку с музыкой', size=18, weight=ft.FontWeight.W_400))
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
                                padding=15
                            ),
                            elevation=5,
                            width=600
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
                    location.controls[0].value = False
                    if loc == location.controls[0].data:
                        location.controls[0].value = True

            timer_action_dd.value = cur_timer['action']
            h, m = "0" * (2 - len(str(cur_timer['time']['hour']))) + f"{cur_timer['time']['hour']}", "0" * (2 - len(str(cur_timer['time']['min']))) + f"{cur_timer['time']['min']}"
            print(h, m)
            timer_time_btn.content.value = f"{h}:{m}"

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
                    ft.Row([ft.FilledTonalButton(text="Сохранить", icon=ft.icons.SAVE, on_click=update_timer, data=value)], alignment=ft.MainAxisAlignment.END, width=600)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER
            )

            page.add(col)
        elif target == "new_timer":
            timer_action_dd.value = None
            timer_time_btn.content.value = "нажмите для выбора"
            for loc in timer_locations.controls:
                loc.controls[0].value = False

            col = ft.Column(
                controls=[
                    ft.Card(
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text("Время", size=18, weight=ft.FontWeight.W_400), timer_time_btn
                                ]
                            ),
                            padding=15
                        ),
                        elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Действие", size=18, weight=ft.FontWeight.W_400), timer_action_dd
                                ],
                                width=600
                            ),
                            padding=15
                        ),
                        elevation=5
                    ),
                    ft.Card(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Место", size=18, weight=ft.FontWeight.W_400), timer_locations
                                ]
                            ),
                            padding=15
                        ),
                        elevation=5
                    ),
                    ft.Row([ft.FilledTonalButton(text="Сохранить", icon=ft.icons.SAVE, on_click=add_new_timer)], alignment=ft.MainAxisAlignment.END, width=600)
                ],
                width=600
            )
            page.add(col)
        page.update()

    def add_new_timer(e: ft.ControlEvent):
        config = load_config()
        schedule = config['schedule']

        sources = []
        for location in timer_locations.controls:
            if location.controls[0].value:
                sources.append(location.controls[0].data)

        if timer_action_dd.value == "play":
            job = scheduler.add_job(play_music, 'cron', hour=timer_datepicker.value.hour, minute=timer_datepicker.value.minute)

        elif timer_action_dd.value == "pause":
            job = scheduler.add_job(stop_music, 'cron', hour=timer_datepicker.value.hour, minute=timer_datepicker.value.minute)

        data = {
            "time": {
                "hour": timer_datepicker.value.hour,
                "min": timer_datepicker.value.minute
            },
            "action": timer_action_dd.value,
            "active": True,
            "sources": sources,
            "job_id": job.id
        }

        schedule.append(data)
        config['schedule'] = schedule
        update_config(config)
        open_sb("Таймер создан", ft.colors.GREEN)
        change_screen("schedule")

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
        update_config(config)

        change_screen('schedule')
        open_sb("Таймер сохранён", ft.colors.GREEN)

    def send_new_path(e: ft.ControlEvent):
        data = e.control.data
        client_id, path = data['client_id'], data['path']
        loading_text.value = "Отправка"
        open_dialog(dialog_loading)
        if client_id == 'all':
            for cid in ['sumstage', 'territory', 'conference']:
                send_data_to_ws(
                    client=cid,
                    action="setdir",
                    params=path
                )
        else:
            send_data_to_ws(
                client=client_id,
                action="setdir",
                params=path
            )
        close_dialog(dialog_loading)
        change_screen("main")

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

    timer_time_btn = ft.TextButton(on_click=lambda _: timer_datepicker.pick_time(), content=ft.Text('нажмите для выбора', size=18))
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
        config = load_config()

        schedule = config['schedule']
        scheduler.remove_job(schedule[e.control.data]['job_id'])

        del schedule[e.control.data]
        update_config(config)

        open_sb("Таймер удалён")
        change_screen("schedule")

    def change_timer_status(e: ft.ControlEvent):
        config = load_config()
        schedule = config['schedule']
        schedule[e.control.data]['active'] = e.control.value
        update_config(config)
        job_id = schedule[e.control.data]['job_id']
        if e.control.value:
            try:
                scheduler.resume_job(job_id)
            except Exception:
                job = scheduler.add_job(play_music, 'cron', hour=schedule[e.control.data]['time']['hour'], minute=schedule[e.control.data]['time']['min'])
                schedule[e.control.data]['job_id'] = job.id
                config['schedule'] = schedule
                update_config(config)

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

    def goto_edittimer(e: ft.ControlEvent):
        change_screen("edit_timer", e.control.data)

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

    login_field = ft.TextField(
        label="Код доступа", text_align=ft.TextAlign.CENTER,
        width=250,
        height=70,
        on_submit=lambda _: login(),
        keyboard_type=ft.KeyboardType.NUMBER,
        password=True
    )
    button_login = ft.ElevatedButton("Войти", width=250, on_click=lambda _: login(),
                                     disabled=False, height=50,
                                     icon=ft.icons.KEYBOARD_ARROW_RIGHT_ROUNDED)
    login_col = ft.Column(
        controls=[
            ft.Image(
                src='icons/loading-animation.png',
                height=200
            ),
            login_field,
            button_login
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

    dialog_info = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Container(ft.Text("Веб-сокет", size=20, weight=ft.FontWeight.W_400), expand=True),
                # ft.IconButton(ft.icons.CLOSE_ROUNDED, on_click=lambda _: close_dialog(dialog_info))
            ]
        )
    )

    if ws_status['status']:
        change_screen('login')
    else:
        dialog_info.content = ft.Text(f"Не удалось подключиться к веб-сокету. Перезагрузите его через Коннект и попробуйте ещё раз.\n\nОшибка: {ws_status['error']}", size=17)
        open_dialog(dialog_info)


create_schedule()

if __name__ == '__main__':
    if platform.system() == "Windows":
        ft.app(
            target=main,
            assets_dir='assets',
            # port=8502,
            # view=ft.AppView.WEB_BROWSER
        )
    elif platform.system() == "Linux":
        ft.app(
            target=main,
            assets_dir='assets',
            name='',
            port=8011
        )
