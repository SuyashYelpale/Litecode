from flask import Blueprint, render_template, session, redirect, url_for, request
from app.models import get_db

main = Blueprint("main", __name__)

@main.route('/')
def home():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template("dashboard.html", user=session['user'])

@main.route('/profile', methods=["GET", "POST"])
def profile():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()

    username = session['user']

    # On form submit
    if request.method == "POST":
        name = request.form['name']
        mobile = request.form['mobile']
        whatsapp = request.form.get('whatsapp', '')
        education = request.form['education']
        permanent_address = request.form['permanent_address']
        current_address = request.form.get('current_address', '')

        cursor.execute("""
            UPDATE users SET
                name=%s,
                mobile=%s,
                whatsapp=%s,
                education=%s,
                permanent_address=%s,
                current_address=%s
            WHERE username=%s
        """, (name, mobile, whatsapp, education, permanent_address, current_address, username))
        conn.commit()

    # Get latest user info
    cursor.execute("SELECT name, mobile, whatsapp, education, permanent_address, current_address FROM users WHERE username=%s", (username,))
    result = cursor.fetchone()
    conn.close()

    user_data = {
        'name': result[0],
        'mobile': result[1],
        'whatsapp': result[2],
        'education': result[3],
        'permanent_address': result[4],
        'current_address': result[5],
    }

    return render_template("profile.html", user=session['user'], user_data=user_data)


@main.route('/classes', methods=["GET", "POST"])
def classes():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        cname = request.form['class_name']
        cursor.execute("INSERT INTO classes (name) VALUES (%s)", (cname,))
        conn.commit()

    # Get classes with batch counts
    cursor.execute("""
        SELECT c.id, c.name, COUNT(b.id) as batch_count 
        FROM classes c 
        LEFT JOIN batches b ON c.id = b.class_id 
        GROUP BY c.id, c.name
    """)
    raw_classes = cursor.fetchall()
    
    # Convert tuples to dictionaries for easier template access
    classes = []
    for cls in raw_classes:
        classes.append({
            'id': cls[0],
            'name': cls[1],
            'batch_count': cls[2]
        })
    
    conn.close()
    return render_template("classes.html", user=session['user'], classes=classes)

@main.route('/edit_class/<int:class_id>', methods=["POST"])
def edit_class(class_id):
    conn = get_db()
    cursor = conn.cursor()
    new_name = request.form['new_name']
    cursor.execute("UPDATE classes SET name = %s WHERE id = %s", (new_name, class_id))
    conn.commit()
    conn.close()
    return redirect(url_for('main.classes'))

@main.route('/delete_class/<int:class_id>', methods=["POST"])
def delete_class(class_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM classes WHERE id = %s", (class_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('main.classes'))

@main.route('/class_batches/<int:class_id>')
def class_batches(class_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Get class details
    cursor.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
    class_data = cursor.fetchone()
    
    # Get batches for this class
    cursor.execute("SELECT * FROM batches WHERE class_id = %s", (class_id,))
    batches = cursor.fetchall()
    
    conn.close()
    
    return render_template("class_batches.html", 
                         user=session['user'],
                         class_data=class_data,
                         batches=batches)

@main.route('/add_batch', methods=["POST"])
def add_batch():
    conn = get_db()
    cursor = conn.cursor()
    
    class_id = request.form['class_id']
    batch_name = request.form['batch_name']
    day = request.form['day']
    start_date = request.form['start_date']
    time_slot = request.form['time_slot']
    notes = request.form.get('notes', '')
    
    cursor.execute(
        "INSERT INTO batches (class_id, name, day, start_date, time_slot, notes) VALUES (%s, %s, %s, %s, %s, %s)",
        (class_id, batch_name, day, start_date, time_slot, notes)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('main.class_batches', class_id=class_id))


@main.route('/students', methods=["GET", "POST"])
def students():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        class_id = request.form['class_id']
        cursor.execute("INSERT INTO students (name, email, class_id) VALUES (%s, %s, %s)", (name, email, class_id))
        conn.commit()

    cursor.execute("SELECT students.id, students.name, students.email, classes.name FROM students JOIN classes ON students.class_id = classes.id")
    data = cursor.fetchall()
    cursor.execute("SELECT * FROM classes")
    classes = cursor.fetchall()
    conn.close()
    return render_template("students.html", user=session['user'], students=data, classes=classes)

@main.route('/batches')
def batches():
    return render_template("batches.html", user=session['user'])

@main.route('/placed-students')
def placed_students():
    return render_template("placed_students.html", user=session['user'])

@main.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))

@main.route('/about')
def about():
    return render_template("about.html")

@main.route('/contact', methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Log or email the message – (here, just print for now)
        print(f"[CONTACT] Name: {name}, Email: {email}, Message: {message}")

        return render_template("contact.html", success=True)
    return render_template("contact.html", success=False)

