from playhouse.migrate import *

db = SqliteDatabase('dbb.sqlite')
migrator = SqliteMigrator(db)

data = TextField()

migrate(
    migrator.alter_column_type('message', 'data', data),
)
