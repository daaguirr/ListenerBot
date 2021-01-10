from flask import Flask
from flask import request

from main import run_prod

app = Flask(__name__)


@app.route(f"/", methods=["GET", "POST"])
def receive():
    try:
        update = request.json
        run_prod(update)
        return ""
    except Exception as e:
        print(e)
        return ""
