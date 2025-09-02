from flask import Blueprint, request, redirect, url_for, abort
from flask_login import login_required, current_user
from models import db, Document, DocumentShare, User, ROLE_OWNER, ROLE_EDITOR, ROLE_ANNOTATOR, ROLE_VIEWER


share_bp = Blueprint("share", __name__, url_prefix="/share")

@share_bp.post("/<int:doc_id>")
@login_required
def grant(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.owner_id != current_user.id:
        abort(403)
    username = (request.form.get("username") or "").strip()
    role = (request.form.get("role") or ROLE_VIEWER)
    if role not in {ROLE_OWNER, ROLE_EDITOR, ROLE_ANNOTATOR, ROLE_VIEWER}:
        role = ROLE_VIEWER
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
        db.session.add(user)
        db.session.commit()
    existing = DocumentShare.query.filter_by(document_id=doc.id, user_id=user.id).first()
    if existing:
        existing.role = role
    else:
        db.session.add(DocumentShare(document_id=doc.id, user_id=user.id, role=role))
    db.session.commit()
    return redirect(url_for("docs.edit_doc", doc_id=doc.id))