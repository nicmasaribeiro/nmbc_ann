# app.py
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, current_user  # <-- add current_user
from config import Dev
from models import db, User

login = LoginManager()
login.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.config.from_object(Dev)

    db.init_app(app)
    Migrate(app, db)

    # Initialize Flask-Login
    login.init_app(app)

    # Ensure templates always have `current_user`
    @app.context_processor
    def inject_current_user():
        return dict(current_user=current_user)

    @login.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

    from blueprints.auth_bp import auth_bp
    from blueprints.documents_bp import docs_bp
    from blueprints.annotations_bp import ann_bp
    from blueprints.sharing_bp import share_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(ann_bp)
    app.register_blueprint(share_bp)

    # app.py (replace your index() route)
    from sqlalchemy import or_
    from flask_login import current_user
    from models import Document, DocumentShare

    @app.get("/")
    def index():
        if getattr(current_user, "is_authenticated", False):
            docs = (
                Document.query
                .outerjoin(DocumentShare, Document.id == DocumentShare.document_id)
                .filter(
                    or_(
                        Document.owner_id == current_user.id,
                        DocumentShare.user_id == current_user.id
                    )
                )
                .order_by(Document.updated_at.desc())
                .distinct()
                .all()
            )
        else:
            # show public docs to logged-out visitors
            docs = (Document.query
                    .filter_by(is_public=True)
                    .order_by(Document.updated_at.desc())
                    .all())
        return render_template("index.html", docs=docs)


    return app
