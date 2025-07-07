from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import get_db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user, pwd))
        user_data = cursor.fetchone()
        conn.close()

        if user_data:
            session['user'] = user
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid credentials")
    return render_template("login.html")


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user, pwd))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('auth.login'))
        except:
            flash("Username already exists.")
        finally:
            conn.close()
    return render_template("register.html")
