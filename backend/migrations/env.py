from alembic import context
from app.db import Base, database_url, engine_for

url = database_url()
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = engine_for(url)
    with engine.begin() as connection:
        context.configure(
            connection=connection, target_metadata=Base.metadata, render_as_batch=True
        )
        context.run_migrations()
    engine.dispose()
