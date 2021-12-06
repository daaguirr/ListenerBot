import base64
import datetime

import requests
from environs import Env
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from flask_restful import Resource, Api, reqparse

import logging

from models import Listener, Message

env = Env()
env.read_env()

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = env.str("SECRET_KEY")
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

api = Api(app, prefix='/listener_bot_api')


@app.route(f"/listener_bot_api", methods=["GET", "POST"])
def receive():
    return {}, 200


class ListenerAdmin(ModelView):
    ...


class MessageAdmin(ModelView):
    ...


ping_parser = reqparse.RequestParser()
ping_parser.add_argument('key', required=True)


class Ping(Resource):
    # noinspection PyMethodMayBeStatic
    def post(self):
        data = ping_parser.parse_args()
        dt = datetime.datetime.utcnow()

        listener = Listener.get(Listener.key == data["key"])

        if listener.enable:
            Message.create(listener=listener, data="PING", timestamp=dt)
            return {}, 200
        return {}, 403


api.add_resource(Ping, '/ping')

update_parser = reqparse.RequestParser()
update_parser.add_argument('key', required=True)
update_parser.add_argument('data', required=True)


class Update(Resource):

    # noinspection PyMethodMayBeStatic
    def notify(self, chat_id, msg):
        requests.post(f"https://api.telegram.org/bot{env.str('BOT_KEY')}/sendMessage",
                      json={'chat_id': chat_id, 'text': msg})

    # noinspection PyMethodMayBeStatic
    def post(self):
        data = update_parser.parse_args()
        dt = datetime.datetime.utcnow()

        listener = Listener.get(Listener.key == data["key"])
        if listener.enable:
            Message.create(listener=listener, data=data["data"], timestamp=dt)
            if listener.notification_header:
                msg = f"{listener.description} listener new message:\n{data['data']}"
            else:
                msg = data['data']
            self.notify(listener.chat_id, msg)
            return {}, 200
        return {}, 403


class UpdateImage(Resource):
    # noinspection PyMethodMayBeStatic
    def notify(self, chat_id, base64_img: str, caption: str, notification_header: bool = True):
        img = base64.b64decode(base64_img)
        if notification_header:
            requests.post(f"https://api.telegram.org/bot{env.str('BOT_KEY')}/sendMessage",
                          json={'chat_id': chat_id, 'text': caption})

        requests.post(f"https://api.telegram.org/bot{env.str('BOT_KEY')}/sendPhoto?chat_id={chat_id}",
                      files={'photo': img})

    def post(self):
        data = update_parser.parse_args()
        dt = datetime.datetime.utcnow()

        listener = Listener.get(Listener.key == data["key"])
        if listener.enable:
            Message.create(listener=listener, data=data["data"], timestamp=dt)
            msg = f"{listener.description} listener new message:\n"
            self.notify(listener.chat_id, data['data'], msg, listener.notification_header)
            return {}, 200
        return {}, 403


api.add_resource(Update, '/update')
api.add_resource(UpdateImage, '/update_image')

admin = Admin(app, url='/listener_bot_api/admin', name='ListenerBotAdmin', template_mode='bootstrap3')

admin.add_view(ListenerAdmin(Listener))
admin.add_view(MessageAdmin(Message))

if __name__ == '__main__':
    try:
        Listener.create_table()
        Message.create_table()
    except:
        pass

    app.run()
