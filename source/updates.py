import threading
import time

import git

import source.global_variables
from source.functions import load_config_file, update_config_file

repo = git.Repo('.')
sha = repo.head.object.hexsha
config_data = load_config_file()
config_data['version'] = sha
update_config_file(config_data)


def check_for_update():
    while True:
        repo = git.Repo('.')

        current_commit = repo.head.commit
        repo.remote().fetch()
        remote_commit = repo.remote().refs['master'].commit
        if current_commit != remote_commit:
            source.global_variables.UPDATE = True
        else:
            source.global_variables.UPDATE = False
        print(source.global_variables.UPDATE)
        time.sleep(20)


def start_check_update():
    update_check_thread = threading.Thread(target=check_for_update)
    update_check_thread.start()
