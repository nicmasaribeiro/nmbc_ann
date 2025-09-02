from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload
from models import db, Document, DocumentVersion, Annotation, AnnotationComment
from services.permissions import can_annotate, can_view

ann_bp = Blueprint("annotations", __name__, url_prefix="/api")

@ann_bp.route("/documents/<int:doc_id>/annotations", methods=["GET"])
def list_annotations(doc_id):
    doc = Document.query.get_or_404(doc_id)
    version = (DocumentVersion.query
               .filter_by(document_id=doc.id)
               .order_by(DocumentVersion.number.desc())
               .first())
    if not version:
        return jsonify([])

    user = current_user if getattr(current_user, "is_authenticated", False) else None

    anns = (Annotation.query
            .options(selectinload(Annotation.comments), selectinload(Annotation.user))
            .filter_by(version_id=version.id)
            .all())

    out = []
    for a in anns:
        content = a.comments[0].text if a.comments else ""
        can_del = False
        if user:
            can_del = (a.user_id == getattr(user, "id", None)) or can_edit(version.document, user)
        out.append({
            "id": a.id,
            "start": a.start_offset,
            "end": a.end_offset,
            "anchor": a.anchor_text,
            "color": a.color,
            "user": a.user.username,
            "content": content,
            "can_delete": can_del,
            "comments": [{"id": c.id, "text": c.text, "user": c.user.username} for c in a.comments]
        })
    return jsonify(out)

@ann_bp.route("/documents/<int:doc_id>/annotations", methods=["POST"])
def create_annotation(doc_id):
    # explicit auth check here so we can share the URL with GET
    if not getattr(current_user, "is_authenticated", False):
        return ("login required", 401)

    doc = Document.query.get_or_404(doc_id)
    if not can_annotate(doc, current_user):
        return ("forbidden: no annotate permission", 403)

    version = (DocumentVersion.query
               .filter_by(document_id=doc.id)
               .order_by(DocumentVersion.number.desc())
               .first())
    if version is None:
        return ("no version to annotate", 400)

    data = request.get_json(force=True) or {}
    try:
        start = int(data.get("start", -1))
        end   = int(data.get("end", -1))
    except Exception:
        start = end = -1

    anchor = (data.get("anchor") or "").strip()
    color  = (data.get("color")  or "yellow").strip()
    note   = (data.get("note")   or "").strip()

    plain = version.rendered_plain or ""
    valid = (0 <= start < end <= len(plain))
    if not valid and anchor:
        pos = plain.find(anchor)
        if pos != -1:
            start, end = pos, pos + len(anchor)
            valid = True
    if not valid:
        return (f"invalid offsets and anchor not found (len={len(plain)})", 400)

    try:
        ann = Annotation(version_id=version.id, user_id=current_user.id,
                         start_offset=start, end_offset=end,
                         anchor_text=anchor or plain[start:end], color=color)
        db.session.add(ann)
        db.session.flush()  # get ann.id

        if note:
            db.session.add(AnnotationComment(annotation_id=ann.id, user_id=current_user.id, text=note))

        db.session.commit()
        return {"id": ann.id}, 201
    except Exception as e:
        db.session.rollback()
        return (f"db error: {e}", 500)

@ann_bp.route("/annotations/<int:ann_id>", methods=["DELETE", "POST"])
def delete_annotation(ann_id):
    # allow form POST or AJAX DELETE
    if not getattr(current_user, "is_authenticated", False):
        return ("login required", 401)
    ann = Annotation.query.get_or_404(ann_id)
    doc = ann.version.document
    if not (ann.user_id == current_user.id or can_edit(doc, current_user)):
        return ("forbidden", 403)
    db.session.delete(ann)
    db.session.commit()
    return {"ok": True}, 200