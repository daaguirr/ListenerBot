import datetime
import os
import subprocess
import time
from difflib import unified_diff
from typing import Tuple

import requests
from environs import Env

env = Env()
env.read_env()

URL_BASE = env.str("URL_BASE")


class Client:
    last_cond_value = None
    last_user_value = None

    ping_interval: int = 60 * 60  # 1 hour
    url_suffix = "update"

    def __init__(self, interval_in_seconds: int, api_key: str):
        assert interval_in_seconds > 1
        self.interval: int = interval_in_seconds
        self.api_key = api_key

    def ping(self):
        try:
            requests.post(f"{URL_BASE}/ping", json={"key": self.api_key})
        except:
            pass

    def on_update(self, cond_data, user_data):
        self.notify(user_data)
        self.last_cond_value = cond_data
        self.last_user_value = user_data

    def run(self):
        try:
            next_ping = 0
            next_loop = 0

            while True:
                if next_ping <= 0:
                    self.ping()
                    next_ping = self.ping_interval
                if next_loop <= 0:
                    cond_data, user_data = self.loop()
                    if self.cond(self.last_cond_value, cond_data):
                        self.on_update(cond_data, user_data)
                    next_loop = self.interval

                next_stop = min(next_loop, next_ping)
                time.sleep(next_stop)

                next_ping -= next_stop
                next_loop -= next_stop

        except KeyboardInterrupt:
            print("Ending client")

    def notify(self, new):
        requests.post(f"{URL_BASE}/{self.url_suffix}", json={"key": self.api_key, 'data': self.on_update_message(new)})

    @staticmethod
    def cond(old, new):
        return old != new

    def loop(self) -> Tuple[str, str]:
        raise NotImplementedError

    def on_update_message(self, new):
        raise NotImplementedError


class ImageClient(Client):
    url_suffix = "update_image"

    def loop(self) -> Tuple[str, str]:
        raise NotImplementedError

    def on_update_message(self, new):
        raise NotImplementedError


class ListenFileClient(Client):
    path: str

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = path

    def on_update_message(self, new):
        diff = ''.join(unified_diff(self.last_user_value, new))
        return f"Update at {self.last_cond_value} on file {self.path} with value: \n\n{diff}"

    def loop(self):
        update = os.path.getmtime(self.path) if os.path.exists(self.path) else None
        if update is None:
            return None
        date = datetime.datetime.fromtimestamp(update)
        with open(self.path, 'r') as file:
            value = file.read().splitlines(keepends=True)

        return date.isoformat(), value


class ListenProcessClient(Client):
    pk: str

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pk = pk

    def on_update_message(self, new):
        response = f'Process with pk={self.pk} updated\nfrom : {self.last_user_value}\nto: '
        if new == '':
            response += "finished"
        else:
            response += str(new)
        return response

    def loop(self):
        p1 = subprocess.Popen(["ps", "-o", "pid=", "-p", self.pk], stdout=subprocess.PIPE)
        res = p1.communicate()
        return res[0].decode(), res[0].decode()
