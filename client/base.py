import datetime
import os
import subprocess
import time

import requests
from environs import Env

env = Env()
env.read_env()

URL_BASE = env.str("URL_BASE")


class Client:
    last = None
    ping_interval: int = 60 * 60  # 1 hour

    def __init__(self, interval_in_seconds: int, api_key: str):
        assert interval_in_seconds > 60
        self.interval: int = interval_in_seconds
        self.api_key = api_key

    def loop(self):
        raise NotImplementedError

    def ping(self):
        requests.post(f"{URL_BASE}/ping", json={"key": self.api_key})

    def run(self):
        try:
            self.ping()
            new = self.loop()
            self.notify(new)

            next_ping = self.ping_interval
            next_loop = self.interval

            while True:
                if next_ping <= 0:
                    self.ping()
                    next_ping = self.ping_interval
                if next_loop <= 0:
                    new = self.loop()
                    if new != self.last:
                        self.notify(new)
                        self.last = new

                    next_loop = self.interval

                next_stop = min(self.interval, self.ping_interval)
                time.sleep(next_stop)

                next_ping -= next_stop
                next_loop -= next_stop

        except KeyboardInterrupt:
            print("Ending client")

    def notify(self, new):
        requests.post(f"{URL_BASE}/update", json={"key": self.api_key, 'data': self.on_update_message(new)})

    def on_update_message(self, new):
        raise NotImplementedError


class ListenFileClient(Client):
    path: str

    def __init__(self, path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = path

    def on_update_message(self, new):
        with open(self.path, 'r') as file:
            value = file.read()
        return f"Update at {self.last} on file {self.path} with value: \n\n {value}"

    def loop(self):
        update = os.path.getmtime(self.path) if os.path.exists(self.path) else None
        if update is None:
            return None
        date = datetime.datetime.fromtimestamp(update)
        return date.isoformat()


class ListenProcessClient(Client):
    pk: str

    def __init__(self, pk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pk = pk

    def on_update_message(self, new):
        response = f'Process with pk={self.pk} updated\nfrom : {self.last}\nto: '
        if new == '':
            response += "finished"
        else:
            response += str(new)
        return response

    def loop(self):
        p1 = subprocess.Popen(["ps", "-o", "pid=", "-p", self.pk], stdout=subprocess.PIPE)
        res = p1.communicate()
        if res[0] == b'':
            return f'Finished process with pk={self.pk}'
        return res[0].decode()
