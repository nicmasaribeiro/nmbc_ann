from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.get("/register")
def register_form():
    return render_template("register.html")

@auth_bp.post("/register")
def register_submit():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "")
    confirm  = (request.form.get("confirm") or "")

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("auth.register_form"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("auth.register_form"))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register_form"))
    if User.query.filter_by(username=username).first():
        flash("Username is taken.", "error")
        return redirect(url_for("auth.register_form"))

    u = User(username=username, password_hash="")
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    flash("Account created. You can log in now.", "success")
    return redirect(url_for("auth.login_form"))

@auth_bp.get("/login")
def login_form():
    return render_template("login.html")

@auth_bp.post("/login")
def login_submit():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "")
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash("Invalid username or password.", "error")
        return redirect(url_for("auth.login_form"))
    login_user(user)
    flash("Welcome!", "success")
    return redirect(url_for("index"))

@auth_bp.post("/logout")
@login_required
def logout_submit():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("index"))
