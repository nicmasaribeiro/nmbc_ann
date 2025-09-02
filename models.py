import datetime as dt
from flask_login import UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

ROLE_OWNER = "owner"
ROLE_EDITOR = "editor"
ROLE_ANNOTATOR = "annotator"
ROLE_VIEWER = "viewer"
ROLE_ORDER = {ROLE_VIEWER: 1, ROLE_ANNOTATOR: 2, ROLE_EDITOR: 3, ROLE_OWNER: 4}

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(64), index=True, unique=True)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    owner = db.relationship("User")
    versions = db.relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.number"
    )

class DocumentVersion(db.Model):
    __tablename__ = "document_versions"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True, nullable=False)
    number = db.Column(db.Integer, nullable=False)
    source_md = db.Column(db.Text, nullable=False)
    rendered_html = db.Column(db.Text, nullable=False)
    rendered_plain = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    document = db.relationship("Document", back_populates="versions")
    annotations = db.relationship("Annotation", backref="version", cascade="all, delete-orphan")

class Annotation(db.Model):
    __tablename__ = "annotations"
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("document_versions.id"), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    start_offset = db.Column(db.Integer, nullable=False)
    end_offset = db.Column(db.Integer, nullable=False)
    anchor_text = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(16), default="#ffeb3b")
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
    user = db.relationship("User")

    # Add/replace this relationship definition
    comments = db.relationship(
        "AnnotationComment",
        backref="annotation",
        cascade="all, delete-orphan",
        order_by="AnnotationComment.id.asc()",   # first comment = original note
        lazy="selectin"
    )

class AnnotationComment(db.Model):
    __tablename__ = "annotation_comments"
    id = db.Column(db.Integer, primary_key=True)
    annotation_id = db.Column(db.Integer, db.ForeignKey("annotations.id"), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    user = db.relationship("User")

class DocumentShare(db.Model):
    __tablename__ = "document_shares"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    role = db.Column(db.String(24), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    document = db.relationship("Document", backref="shares")
    user = db.relationship("User")
