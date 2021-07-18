import peewee

db = peewee.SqliteDatabase('dbb.sqlite', check_same_thread=False)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Listener(BaseModel):
    id = peewee.BigAutoField(unique=True)
    chat_id = peewee.CharField()
    key = peewee.CharField()
    description = peewee.CharField()
    enable = peewee.BooleanField(default=True)


class Message(BaseModel):
    id = peewee.BigAutoField(unique=True)
    listener = peewee.ForeignKeyField(Listener, on_delete='CASCADE')
    data = peewee.TextField()
    timestamp = peewee.DateTimeField()
