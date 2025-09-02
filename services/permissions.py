from models import DocumentShare, ROLE_ORDER

def user_role_for(doc, user):
    if user is None:
        return None
    if doc.owner_id == user.id:
        return "owner"
    share = DocumentShare.query.filter_by(document_id=doc.id, user_id=user.id).first()
    return share.role if share else None

def can_view(doc, user):
    return doc.is_public or user_role_for(doc, user) is not None

def can_edit(doc, user):
    role = user_role_for(doc, user)
    return role is not None and ROLE_ORDER[role] >= ROLE_ORDER["editor"]

def can_annotate(doc, user):
    role = user_role_for(doc, user)
    return role is not None and ROLE_ORDER[role] >= ROLE_ORDER["annotator"]