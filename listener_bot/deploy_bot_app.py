from flask import Flask
from flask import request
from main import run_prod
from environs import Env

env = Env()
env.read_env()

app = Flask(__name__)


@app.route(f"/{env.str('BOT_KEY')}", methods=["GET", "POST"])
def receive():
    try:
        update = request.json
        run_prod(update)
        return ""
    except Exception as e:
        print(e)
        return ""
