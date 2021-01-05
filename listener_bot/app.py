import datetime

import requests
from environs import Env
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.peewee import ModelView
from flask_restful import Resource, Api, reqparse

from listener_bot.models import Listener, Message

env = Env()
env.read_env()

app = Flask(__name__)
app.config['SECRET_KEY'] = env.str("SECRET_KEY")
api = Api(app)


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
            msg = f"{listener.description} listener new message:\n{data['data']}"
            self.notify(listener.chat_id, msg=msg)
            return {}, 200
        return {}, 403


api.add_resource(Update, '/update')

if __name__ == '__main__':
    import logging

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
    admin = Admin(app, name='ListenerBotAdmin', template_mode='bootstrap3')

    admin.add_view(ListenerAdmin(Listener))
    admin.add_view(MessageAdmin(Message))

    try:
        Listener.create_table()
        Message.create_table()
    except:
        pass

    app.run()
