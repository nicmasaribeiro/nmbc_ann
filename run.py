from app import create_app
from models import db, User   # <-- importing models here registers ALL tables
# add in app.py (after db.init_app(app) / before returning app)
from sqlalchemy import inspect
from flask_migrate import Migrate
from flask_login import LoginManager, current_user

def _ensure_tables(app):
    with app.app_context():
        insp = inspect(db.engine)
        if 'users' not in insp.get_table_names():
            print("No tables found — creating (dev bootstrap).")
            db.create_all()


if __name__ == '__main__':
    app = create_app()
    _ensure_tables(app)
    app.run('0.0.0.0',90)