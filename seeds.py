# seeds.py
from app import create_app
from models import db, User, Document, DocumentVersion
from services.markdown_render import render

app = create_app()
with app.app_context():
    db.create_all()  # fine for dev; in prod use migrations

    user = User.query.filter_by(username="alice").first()
    if not user:
        user = User(username="alice")
        db.session.add(user)
        db.session.commit()

    doc = Document(title="Sample Doc", owner_id=user.id)
    md = r"""
# Euler–Lagrange
For functional $J[y] = \int_a^b L(x, y, y')\,dx$ the condition is
$$\frac{\partial L}{\partial y} - \frac{d}{dx}\frac{\partial {\partial y'}} = 0.$$
"""
    html, plain = render(md)
    v = DocumentVersion(document=doc, number=1, source_md=md, rendered_html=html, rendered_plain=plain)
    db.session.add_all([doc, v])
    db.session.commit()
    print("Seeded 'alice' and a sample document.")
