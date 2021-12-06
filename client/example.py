import requests

from base import Client


class WebExampleClient(Client):
    @staticmethod
    def cond(old, new):
        return old != new

    def loop(self):
        s = requests.Session()
        res = s.get("https://www.example.com")
        data = res.json()
        return data["condition_field"], data["very_important_field"]

    def on_update_message(self, new):
        return f"Updated\nfrom {self.last_user_value} to\n{new}"


if __name__ == '__main__':
    a = WebExampleClient(api_key="<API-KEY>", interval_in_seconds=60)
    a.run()
