from flet import ScrollMode, IconButton, icons

screens_data = {
    'main': {
        'leading': {
            'icon': None,
            'target': None
        },
        'title': "Audio",
        'scroll': ScrollMode.HIDDEN
    },
    'settings': {
        'leading': {
            'icon': icons.ARROW_BACK,
            'target': 'main'
        },
        'title': "Настройки",
        'scroll': ScrollMode.HIDDEN
    },
    'schedule': {
        'leading': {
            'icon': icons.ARROW_BACK,
            'target': 'main'
        },
        'title': "Расписание",
        'scroll': ScrollMode.HIDDEN
    },
    'pick_folder': {
        'leading': {
            'icon': icons.ARROW_BACK,
            'target': 'main'
        },
        'title': "Выбор папки",
        'scroll': ScrollMode.HIDDEN
    },
    'edit_timer': {
        'leading': {
            'icon': icons.ARROW_BACK,
            'target': 'schedule'
        },
        'title': "Редактирование",
        'scroll': ScrollMode.HIDDEN
    },
    'new_timer': {
        'leading': {
            'icon': icons.ARROW_BACK,
            'target': 'schedule'
        },
        'title': "Новый таймер",
        'scroll': ScrollMode.HIDDEN
    },
    'login': {
        'leading': {
            'icon': None,
            'target': 'schedule'
        },
        'title': "",
        'scroll': None
    }

}
