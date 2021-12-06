from playhouse.migrate import *

db = SqliteDatabase('dbb.sqlite')
migrator = SqliteMigrator(db)

notification_header = BooleanField(default=True)

migrate(
    migrator.add_column('listener', 'notification_header', notification_header),
)
