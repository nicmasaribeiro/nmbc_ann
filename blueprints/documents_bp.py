import secrets
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, flash
from flask_login import login_required, current_user
from models import db, Document, DocumentVersion
from services.markdown_render import render as render_md
from services.permissions import can_view, can_edit, can_annotate
from services.markdown_render import render as render_mdc

docs_bp = Blueprint("docs", __name__, url_prefix="/documents")

@docs_bp.get("/new", endpoint="new_doc_form")
@login_required
def new_doc_form():
    return render_template("document_edit.html", document=None, version=None)

@docs_bp.post("", endpoint="create_doc")
@login_required
def create_doc():
    title = (request.form.get("title") or "Untitled").strip()
    md = request.form.get("markdown") or ""
    doc = Document(title=title, owner_id=current_user.id, share_token=secrets.token_hex(16))
    html, plain = render_md(md)
    v = DocumentVersion(document=doc, number=1, source_md=md, rendered_html=html, rendered_plain=plain)
    db.session.add_all([doc, v])
    db.session.commit()  # <-- critical
    return redirect(url_for("docs.edit_doc", doc_id=doc.id))

@docs_bp.post("/<int:doc_id>/edit", endpoint="save_doc")
@login_required
def save_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if not can_edit(doc, current_user):
        abort(403)
    md = request.form.get("markdown") or ""
    prev = (DocumentVersion.query
            .filter_by(document_id=doc.id)
            .order_by(DocumentVersion.number.desc())
            .first())
    number = (prev.number + 1) if prev else 1
    html, plain = render_md(md)
    v = DocumentVersion(document=doc, number=number, source_md=md, rendered_html=html, rendered_plain=plain)
    db.session.add(v)
    db.session.commit()  # <-- critical
    return redirect(url_for("docs.view_doc", doc_id=doc.id))


@docs_bp.get("/<int:doc_id>/edit", endpoint="edit_doc")
@login_required
def edit_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if not can_edit(doc, current_user):
        abort(403)
    version = (DocumentVersion.query
               .filter_by(document_id=doc.id)
               .order_by(DocumentVersion.number.desc())
               .first())
    return render_template("document_edit.html", document=doc, version=version)

@docs_bp.post("/<int:doc_id>/delete", endpoint="delete_doc")
@login_required
def delete_doc(doc_id):
    from models import DocumentShare  # inline import to avoid cycles if any
    doc = Document.query.get_or_404(doc_id)

    # Owner-only delete (safer). Change to `can_edit` if you prefer editors too.
    if doc.owner_id != current_user.id:
        abort(403)

    # Clean up shares explicitly (versions/annotations already cascade)
    DocumentShare.query.filter_by(document_id=doc.id).delete(synchronize_session=False)

    db.session.delete(doc)  # will cascade to versions -> annotations -> comments
    db.session.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("index"))

@docs_bp.get("/<int:doc_id>", endpoint="view_doc")
def view_doc(doc_id):
    doc = Document.query.get_or_404(doc_id)
    token = request.args.get("t")
    user = current_user if getattr(current_user, "is_authenticated", False) else None
    if not can_view(doc, user) and token != doc.share_token:
        abort(403)
    version = (DocumentVersion.query
               .filter_by(document_id=doc.id)
               .order_by(DocumentVersion.number.desc())
               .first())
    can_annot = can_annotate(doc, user) if user else False
    return render_template("document_view.html", document=doc, version=version, can_annotate=can_annot)

@docs_bp.post("/<int:doc_id>/toggle_public", endpoint="toggle_public")
@login_required
def toggle_public(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.owner_id != current_user.id:
        abort(403)
    doc.is_public = not doc.is_public
    db.session.commit()
    return redirect(url_for("docs.edit_doc", doc_id=doc.id))

@docs_bp.get("/<int:doc_id>/share_link", endpoint="share_link")
@login_required
def share_link(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.owner_id != current_user.id:
        abort(403)
    return jsonify({"share_url": url_for("docs.view_doc", doc_id=doc.id, t=doc.share_token, _external=True)})
