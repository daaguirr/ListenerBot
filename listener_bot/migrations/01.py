from playhouse.migrate import *

db = SqliteDatabase('database.db')
migrator = SqliteMigrator(db)

data = TextField()

migrate(
    migrator.alter_column_type('message', 'data', data),
)
