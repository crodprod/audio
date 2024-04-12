import platform
from datetime import datetime
import os
import time

import requests
import subprocess

from source.schedule_funcs import start_schedule
from source.mixer_funcs import control, set_volume, play_start_sound, start_music_check, send_wss_data
from source.functions import update_config_file, load_config_file
import source.global_variables
import flet as ft
import eyed3

# from source.updates import start_check_update

script_path = os.path.abspath(__file__)
script_directory = os.path.dirname(script_path)
os.chdir(script_directory)
project_folder = os.getcwd()
config_file_name = "audio_config.json"


class Message():
    def __init__(self, data):
        self.data = data


def send_awake():
    config_data = load_config_file()
    url = f'https://api.telegram.org/bot{config_data["bot"]["token"]}/sendMessage'
    data = {'chat_id': config_data['bot']['chat'], 'text': '*Модуль 🔊CROD.Audio перезагружен*',
            "parse_mode": "Markdown"}
    requests.post(url=url, data=data)


def main(page: ft.Page):
    config_data = load_config_file()

    page.title = "Audio"
    page.fonts = {
        "Montserrat": "fonts/Montserrat-SemiBold.ttf",
        "Geologica": "fonts/Geologica.ttf",
        "Geologica-Black": "fonts/Geologica-black.ttf"
    }
    page.theme = ft.Theme(font_family="Montserrat")
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    hf = ft.HapticFeedback()
    page.overlay.append(hf)

    main_appbar = ft.AppBar(
        title=ft.Text('', size=19),
        bgcolor=ft.colors.SURFACE_VARIANT,
        leading=None,
    )

    def on_incoming_message(message: Message):

        config_data = message.data
        vol_slider.value = config_data['volume']
        autoplay_checkbocx.value = source.global_variables.AUTOPLAY
        change_controls_visible()
        fill_playlist()
        song_name.value = config_data['current_track']['name']
        song_author.value = config_data['current_track']['author']
        cur_status.value = config_data['current_track']['cur_status']

        page.update()

    def change_controls_visible():
        btn_prev.visible, btn_next.visible = not source.global_variables.AUTOPLAY, not source.global_variables.AUTOPLAY
        song_name.visible, song_author.visible = not source.global_variables.AUTOPLAY, not source.global_variables.AUTOPLAY
        btn_play.visible = not btn_pause.visible
        print("VISIBLE", btn_prev.visible)
        page.update()

    def send_data():
        page.pubsub.send_others(Message(data=config_data))

    page.pubsub.subscribe(on_incoming_message)

    def open_classic_snackbar(text: str, *args):
        # классический бар

        page.snack_bar = ft.SnackBar(
            content=ft.Row(
                controls=[
                    ft.Text(text, size=16)
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            duration=1500
        )

        if args:
            page.snack_bar.bgcolor = args[0]
            if page.snack_bar.bgcolor in [ft.colors.GREEN, ft.colors.RED]:
                page.snack_bar.content.controls[0].color = ft.colors.WHITE

        page.snack_bar.open = True
        page.update()

    def check_pin_field(e: ft.ControlEvent):
        # проверка корректности пин-кода

        pin = e.control.value
        if pin:
            btn_go.disabled = False
        else:
            btn_go.disabled = True
        page.update()

    def check_pin(e: ft.ControlEvent):
        # проверка пин-кода

        hf.medium_impact()
        pin = password_field.value
        if pin == "1111":
            password_field.border_color = ft.colors.GREEN
            password_field.value = ""
            page.update()
            change_screens("main")
            password_field.border_color = ft.colors.SURFACE_VARIANT
            btn_go.disabled = True
        else:
            password_field.border_color = ft.colors.RED
            page.update()
            time.sleep(2)
            password_field.border_color = ft.colors.SURFACE_VARIANT
            page.update()

    def sender(e: ft.ControlEvent):
        if e.control.data == "autoplay_changed":
            autoplay_checkbox_value_changed()
        elif e.control.data == "transmit_changed":
            transmit_checkbox_value_changed()
        else:
            change_screens(e.control.data)

    def insert_to_queue(e: ft.ControlEvent):
        config_data = load_config_file()
        new_index = config_data['current_track']['index'] + 1
        config_data['playlist'].remove(e.control.data)
        config_data['playlist'].insert(new_index, e.control.data)
        update_config_file(config_data)
        playing_process("next")

    def playing_process(action):
        print("ACTION", action)
        data = control(action)
        if action in ['next', 'prev']:
            btn_play.visible = False
            btn_pause.visible = True
            cur_status.value = "играет в данный момент"

            track_name_author = eyed3.load(data)

            song_name.value = track_name_author.tag.title
            if song_name.value == "":
                song_name.value = os.path.basename(data)
            song_author.value = track_name_author.tag.artist
            if song_author.value == "":
                song_author.value = "---"

            config_data['current_track']['cur_status'] = cur_status.value
            config_data['current_track']['name'] = song_name.value
            config_data['current_track']['author'] = song_author.value

            # page.update()

        elif action == "play":
            cur_status.value = "играет в данный момент"
            btn_play.visible = False
            btn_pause.visible = True
        elif action == "pause":
            if autoplay_checkbocx.value:
                autoplay_checkbocx.value = False
                autoplay_checkbox_value_changed()
            btn_play.visible = True
            btn_pause.visible = False
            cur_status.value = "на паузе в данный момент"
        page.update()
        send_data()

    def track_controls_btns_pressed(e: ft.ControlEvent):
        # кнопки управления воспроизведением нажаты

        hf.medium_impact()
        action = e.control.data
        actions = {
            "play": "Воспроизведение",
            "pause": "Пауза",
            "next": "Следующий трек",
            "prev": "Предыдущий трек"
        }
        open_classic_snackbar(actions[action])
        playing_process(action)
        send_data()

    def vol_slider_changed(e: ft.ControlEvent):
        # слайдер громкости изменился

        volume = int(e.control.value)
        set_volume(volume / 100)
        config_data['volume'] = volume
        vol_value.value = f"{volume}%"
        update_config_file(config_data)
        send_data()

    def transmit_checkbox_value_changed():
        value = transmit_checkbox.value
        if value:
            send_wss_data('activate')
            open_classic_snackbar("Трансляция включена")
        else:
            send_wss_data('deactivate')
            open_classic_snackbar("Трансляция выключена")
        send_data()
    def autoplay_checkbox_value_changed():
        # Изменение автовоспроизведения

        value = autoplay_checkbocx.value
        if value:
            open_classic_snackbar("Автоплей")
            cur_status.value = "автоплей"
            btn_play.visible = False
            btn_pause.visible = True
        else:
            open_classic_snackbar("Ручное управление")
            cur_status.value = "ручное управление"
            btn_play.visible = False
            btn_pause.visible = True

        source.global_variables.AUTOPLAY = value
        change_controls_visible()

        send_data()
        page.update()

    def find_mp3_files(directory):
        mp3_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".mp3"):
                    mp3_files.append(os.path.join(root, file))

        return mp3_files

    def update_current_folder(e: ft.ControlEvent):
        if platform.system() == 'Windows':
            new_folder = os.path.join("music", e.control.data)
        else:
            new_folder = os.path.join("/home/pi/music/Sumstage/livemusic", e.control.data)
        playlist = find_mp3_files(new_folder)
        if len(playlist) == 0:
            open_classic_snackbar("В папке нет музыки", ft.colors.RED)
        else:
            config_data['current_track']['index'] = -1
            config_data['current_dir'] = e.control.data
            config_data['playlist'] = playlist
            update_config_file(config_data)
            change_screens('main')
            open_classic_snackbar(f"Выбрана папка {e.control.data}")
            playing_process("next")
            send_data()

    def schedule_editor(e: ft.ControlEvent):
        # управление выбранным расписанием

        config_data = load_config_file()

        data = e.control.data
        action, timer_id = data[0], data[1]

        schedule_list = config_data['schedule']
        for index, timer in enumerate(schedule_list):
            if timer['id'] == timer_id:
                if action == "switch":
                    config_data['schedule'][index]['active'] = not timer['active']
                    update_config_file(config_data)
                    open_classic_snackbar("Таймер переключен")
                elif action == "delete":
                    config_data['schedule'].remove(timer)
                    update_config_file(config_data)
                    open_classic_snackbar("Таймер удалён")

                get_schedule()
                page.update()
                break
        if action == "edit":
            print(e.control.data)
            source.global_variables.edit_timer_data = e.control.data
            print(source.global_variables.edit_timer_data)
            timer = source.global_variables.edit_timer_data[1]
            timer_time_btn.text = f"{timer['hours']}:{timer['minutes']}"
            timer_time_picker.value = f"{timer['hours']}:{timer['minutes']}"

            if timer['action'] == "next":
                timer_action_dd.value = "Включение"
            else:
                timer_action_dd.value = "Выключение"

            page.dialog = dialog_edit_timer
            dialog_edit_timer.open = True
            page.update()

    def get_schedule():
        config_data = load_config_file()

        timers = config_data['schedule']
        timers_list.controls.clear()

        actions = {
            "next": "Включение",
            "pause": "Выключение",
        }
        icons = {
            "next": [ft.icons.VOLUME_UP_ROUNDED, ft.colors.GREEN],
            "pause": [ft.icons.VOLUME_OFF_ROUNDED, ft.colors.RED]
        }

        for timer in timers:

            last_call = ft.Text(size=16)

            if timer['active']:
                if str(datetime.now().date()) == timer['last_action']:
                    last_call.value = "Завтра"
                else:
                    last_call.value = "Сегодня"
            else:
                last_call.value = "Отключен"

            timer_card = ft.Card(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(icons[timer['action']][0], color=ft.colors.WHITE, size=25),
                                    ft.Text(f"{actions[timer['action']]} в {timer['hours']}:{timer['minutes']}",
                                            size=19)
                                ],
                                alignment=ft.MainAxisAlignment.START
                            ),
                            ft.Row(
                                [
                                    ft.Switch(
                                        value=timer['active'], data=['switch', timer['id']],
                                        on_change=schedule_editor, active_color=ft.colors.GREEN,
                                        inactive_thumb_color=ft.colors.RED,
                                    ),
                                    last_call,
                                ]
                            ),
                            ft.Row(
                                [
                                    ft.ElevatedButton(
                                        icon=ft.icons.EDIT_ROUNDED,
                                        color=ft.colors.WHITE,
                                        text="Изменить",
                                        on_click=schedule_editor,
                                        data=['edit', timer],
                                    ),
                                    ft.ElevatedButton(
                                        icon=ft.icons.DELETE_ROUNDED,
                                        color=ft.colors.WHITE,
                                        text="Удалить",
                                        on_click=schedule_editor,
                                        data=['delete', timer['id']]
                                    )
                                ]
                            ),
                        ]
                    ),
                    padding=15
                ),
                width=500
            )
            timers_list.controls.append(timer_card)

    def update_timer_action(e):
        config_data = load_config_file()
        print(source.global_variables.edit_timer_data)
        for index, timer in enumerate(config_data['schedule']):
            if timer['id'] == source.global_variables.edit_timer_data[1]['id']:
                if e.control.value == "Включение":
                    action = "next"
                else:
                    action = "pause"

                config_data['schedule'][index]['action'] = action
                update_config_file(config_data)
                open_classic_snackbar("Действие изменено")
                break

    def update_timer_time(e):
        config_data = load_config_file()
        print(source.global_variables.edit_timer_data)
        for index, timer in enumerate(config_data['schedule']):
            if timer['id'] == source.global_variables.edit_timer_data[1]['id']:
                config_data['schedule'][index]['hours'] = str(e.control.value.hour)
                config_data['schedule'][index]['minutes'] = "0" * (2 - len(str(e.control.value.minute))) + str(
                    e.control.value.minute)
                update_config_file(config_data)
                timer_time_btn.text = f"{str(e.control.value.hour)}:{config_data['schedule'][index]['minutes']}"
                open_classic_snackbar("Время изменено")
                break

        page.update()

    def reboot(e: ft.ControlEvent):
        # Получение обновлений с гита и перезапуск systemctl
        reboot_pin = password_field.value

        script_path = f'{project_folder}/synco.sh'

        dialog_reboot = ft.AlertDialog(modal=True, content=ft.Column(
            width=400, height=150,
            controls=[ft.Text("Приложение обновляется и будет перезапущено. После звукового сигнала откройте его снова",
                              size=16, text_align=ft.TextAlign.CENTER),
                      ft.ProgressBar()],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ))

        if reboot_pin == "6387":
            page.dialog = dialog_reboot
            dialog_reboot.open = True
            page.update()

            time.sleep(2)
            dialog_reboot.open = False

            try:
                control("pause")
                play_start_sound("reboot")
                subprocess.run([script_path], check=True)
            except Exception as e:
                open_classic_snackbar(f"Ошибка перезагрузки", ft.colors.RED)
                print(f"Ошибка при выполнении команды: {e}")
        else:
            password_field.value = ""
            password_field.border_color = ft.colors.RED
            page.update()
            time.sleep(2)
            password_field.border_color = ft.colors.SURFACE_VARIANT
        page.update()

    def fill_playlist():
        config_data = load_config_file()
        added = []
        print(added)
        playlist.controls.clear()
        for track in set(config_data['playlist']):
            song = eyed3.load(track).tag.title
            if song == "":
                song = os.path.basename(track)

            if song not in added:
                print(song, added)
                playlist.controls.append(
                    ft.Container(
                        ft.TextButton(
                            text=song, on_click=insert_to_queue, data=track,
                            style=ft.ButtonStyle(color=ft.colors.WHITE),
                        ),
                        margin=ft.margin.only(bottom=-10)
                    )
                )
                added.append(song)
        page.update()

    def change_screens(target):
        # изменение экранов

        page.clean()
        page.appbar = None
        main_appbar.actions = None
        page.navigation_bar = None
        page.scroll = None
        page.floating_action_button = None

        if target == "login":
            password_field.on_change = check_pin_field
            btn_go.on_click = check_pin
            page.add(ft.Container(content=screen_login, expand=True))

        elif target == "main":
            config_data = load_config_file()

            song_name.value, song_author.value = config_data['current_track']['name'], config_data['current_track'][
                'author']
            vol_slider.value = config_data['volume']
            vol_value.value = f"{config_data['volume']}%"
            set_volume(config_data['volume'] / 100)
            autoplay_checkbocx.value = source.global_variables.AUTOPLAY
            autoplay_checkbox_value_changed()
            fill_playlist()
            page.appbar = main_appbar
            main_appbar.title.value = "Воспроизведение"
            main_appbar.leading = ft.IconButton(
                icon=ft.icons.EXIT_TO_APP_ROUNDED,
                on_click=sender,
                data="login"
            )
            page.add(screen_main)

        elif target == "pick_folder":
            config_data = load_config_file()

            page.appbar = main_appbar
            main_appbar.title.value = "Выбор папки"
            main_appbar.leading = ft.IconButton(
                icon=ft.icons.ARROW_BACK_ROUNDED,
                data="main",
                on_click=sender
            )

            directories = [d for d in os.listdir('/home/pi/music/Sumstage/livemusic') if
                           os.path.isdir(os.path.join('/home/pi/music/Sumstage/livemusic', d))]
            folders_list.controls.clear()
            if len(directories) > 0:
                text = "Выберите папку, из которой необходимо играть музыку"
                control_row.disabled = False
                autoplay_checkbocx.disabled = False
            else:
                text = "Папок с музыкой нет, загрузите их в память и попробуйте снова"
                control_row.disabled = True
                autoplay_checkbocx.disabled = True
            folders_list.controls.append(
                ft.Text(text,
                        width=300,
                        text_align=ft.TextAlign.CENTER,
                        size=16
                        )
            )
            for dir in directories:
                print(dir, config_data['current_dir'])
                folder_btn = ft.ElevatedButton(
                    "Выбрать",
                    color=ft.colors.WHITE,
                    data=dir,
                    on_click=update_current_folder
                )
                folder_icon = ft.Icon(ft.icons.FOLDER_ROUNDED)

                if os.path.basename(dir) == os.path.basename(config_data['current_dir']):
                    folder_btn.disabled = True
                    folder_btn.text = "Текущая"
                    folder_icon = ft.Icon(ft.icons.FOLDER_SHARED_ROUNDED)

                dir_row = ft.Row(
                    [
                        folder_icon,
                        ft.Text(os.path.basename(dir), width=150, size=17),
                        folder_btn
                    ],
                    alignment=ft.MainAxisAlignment.CENTER
                )
                folders_list.controls.append(dir_row)

            page.add(screen_folders)

        elif target == "schedule":

            page.appbar = main_appbar
            main_appbar.title.value = "Расписание"
            main_appbar.leading = ft.IconButton(
                icon=ft.icons.ARROW_BACK_ROUNDED,
                data="main",
                on_click=sender
            )
            page.floating_action_button = ft.FloatingActionButton(
                icon=ft.icons.EDIT_CALENDAR_ROUNDED
            )

            get_schedule()
            page.add(screen_schedule)

        else:
            page.add(
                ft.Column(
                    [
                        ft.Text("Упс, на этой странице ещё ничего нет...", size=30, font_family="Montserrat"),
                        ft.ElevatedButton(
                            "Назаааааааад",
                            icon=ft.icons.ARROW_BACK_ROUNDED,
                            data="main",
                            on_click=sender,
                            color=ft.colors.WHITE
                        )
                    ]
                )
            )

        page.update()

    password_field = ft.TextField(
        label="Код доступа",
        width=250,
        password=True,
        on_submit=check_pin,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
        border_width=2
    )

    btn_go = ft.ElevatedButton(
        text="Войти",
        color=ft.colors.WHITE,
        # on_long_press=reboot,
        icon=ft.icons.KEYBOARD_ARROW_RIGHT_ROUNDED,
        disabled=True,
        width=250,
        height=50
    )

    update_text = ft.Text("Новое обновление доступно!", size=14, text_align=ft.TextAlign.CENTER, visible=False)
    version_text = ft.Text("")
    screen_login = ft.Column(
        [
            ft.Column(
                [
                    ft.Text("Audio", size=35, font_family="Montserrat", text_align=ft.TextAlign.CENTER),
                    password_field,
                    btn_go,
                    update_text
                ],
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    version_text
                ],
                alignment=ft.MainAxisAlignment.START
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    btn_play = ft.IconButton(
        icon=ft.icons.PLAY_ARROW_ROUNDED,
        icon_size=50,
        data="play",
        on_click=track_controls_btns_pressed,
        icon_color=ft.colors.WHITE
    )

    btn_pause = ft.IconButton(
        icon=ft.icons.PAUSE_ROUNDED,
        icon_size=50,
        data="pause",
        on_click=track_controls_btns_pressed,
        icon_color=ft.colors.WHITE
    )

    btn_next = ft.IconButton(
        icon=ft.icons.SKIP_NEXT_ROUNDED,
        icon_size=35,
        data="next",
        on_click=track_controls_btns_pressed,
        icon_color=ft.colors.WHITE
    )

    btn_prev = ft.IconButton(
        icon=ft.icons.SKIP_PREVIOUS_ROUNDED,
        icon_size=35,
        data="prev",
        on_click=track_controls_btns_pressed,
        icon_color=ft.colors.WHITE
    )

    btn_pick_folders = ft.ElevatedButton(
        "Выбор папки",
        color=ft.colors.WHITE,
        icon=ft.icons.CREATE_NEW_FOLDER_ROUNDED,
        data="pick_folder",
        on_click=sender
    )

    btn_timers = ft.ElevatedButton(
        "Расписание",
        color=ft.colors.WHITE,
        icon=ft.icons.SCHEDULE_ROUNDED,
        data="schedule",
        on_click=sender
    )

    vol_slider = ft.Slider(
        value=config_data['volume'] / 100,
        min=0, max=100,
        divisions=100,
        label="{value}%", width=300,
        active_color=ft.colors.WHITE,
        on_change=vol_slider_changed
    )

    vol_value = ft.Text(size=17)

    autoplay_checkbocx = ft.Checkbox(
        label="Автоматическое переключение",
        data="autoplay_changed",
        on_change=sender,
        adaptive=True
    )

    transmit_checkbox = ft.Checkbox(
        label="Трансляция",
        data="transmit_changed",
        on_change=sender,
        adaptive=True
    )

    control_row = ft.Row(
        [
            btn_prev, btn_play, btn_pause, btn_next
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    cur_status = ft.Text("")
    song_name = ft.Text("---", size=24)
    song_author = ft.Text("---", size=20)
    playlist = ft.Column(alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.START,
                         scroll=ft.ScrollMode.ADAPTIVE, height=200, width=300)

    screen_main = ft.Column(
        [
            ft.Column(
                [
                    # ft.Text("Текущий плейлист", size=18),
                    # playlist,
                    ft.Container(ft.Divider(thickness=2), width=300),
                    song_name,
                    ft.Container(
                        song_author,
                        margin=ft.margin.only(top=-15)
                    ),
                    # cur_status,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            control_row,
            ft.Row(
                [
                    ft.Icon(ft.icons.VOLUME_UP_ROUNDED, color=ft.colors.WHITE),
                    ft.Container(
                        vol_slider,
                        margin=ft.margin.only(left=-25, right=-25)
                    ),
                    vol_value

                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                [
                    autoplay_checkbocx
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                [
                    transmit_checkbox
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row(
                [
                    btn_pick_folders, btn_timers
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )

    folders_list = ft.Column(
        # scroll=ft.ScrollMode.ADAPTIVE
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )

    timers_list = ft.Column(
        scroll=ft.ScrollMode.ADAPTIVE,
        alignment=ft.MainAxisAlignment.START,
    )

    screen_folders = ft.Column(
        [
            folders_list
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        # scroll=ft.ScrollMode.ADAPTIVE
    )

    screen_schedule = ft.Column(
        [
            timers_list
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        scroll=ft.ScrollMode.ADAPTIVE
    )

    timer_time_picker = ft.TimePicker(
        time_picker_entry_mode=ft.TimePickerEntryMode.DIAL_ONLY,
        help_text="Выберите время активации",
        confirm_text="Сохранить",
        cancel_text="Назад",
        error_invalid_text="Неправильный формат",
        on_change=update_timer_time
    )
    page.overlay.append(timer_time_picker)
    timer_time_btn = ft.ElevatedButton(
        "Изменить время",
        on_click=lambda _: timer_time_picker.pick_time(),
        color=ft.colors.WHITE,
        icon=ft.icons.ACCESS_TIME_ROUNDED
    )
    timer_action_dd = ft.Dropdown(
        # width=100,
        options=[
            ft.dropdown.Option("Включение"),
            ft.dropdown.Option("Выключение"),
        ],
        on_change=update_timer_action
    )

    dialog_edit_timer = ft.AlertDialog(
        modal=True,
        title=ft.Text("Изменение", size=20),
        content=ft.Column(
            [
                ft.Text("Время активации", size=18),
                timer_time_btn,
                ft.Container(ft.Divider(thickness=1)),
                ft.Text("Действие", size=18),
                timer_action_dd
            ],
            height=250,
            width=400
        ),
        actions=[
            ft.ElevatedButton(
                text="Назад",
                icon=ft.icons.ARROW_BACK_ROUNDED,
                color=ft.colors.WHITE,
                on_click=lambda _: close_dialog(dialog_edit_timer)
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )

    def close_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        get_schedule()
        page.update()

    # print("!!!!!!", source.global_variables.UPDATE)
    # if source.global_variables.UPDATE:
    #     update_text.visible = True
    # else:
    #     update_text.visible = False

    version_text.value = f"CROD.Audio (сборка {config_data['version'][:7]})"
    page.update()
    change_screens("login")


DEFAULT_FLET_PATH = ''
flet_path = os.getenv("FLET_PATH", DEFAULT_FLET_PATH)
if __name__ == "__main__":
    play_start_sound("start")
    # start_check_update()
    start_music_check()
    start_schedule()
    if platform.system() == 'Windows':
        ft.app(
            target=main,
            assets_dir='assets'
        )
    else:
        send_awake()
        ft.app(
            name=flet_path,
            target=main,
            view=None,
            port=8502,
            assets_dir="assets"
        )
