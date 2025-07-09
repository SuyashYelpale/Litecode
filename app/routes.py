from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import get_db
from flask import abort
from datetime import datetime

main = Blueprint("main", __name__)

@main.route('/')
def home():
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template("dashboard.html")

@main.route('/profile', methods=["GET", "POST"])
def profile():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()

    username = session['user']

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

    cursor.execute("""
        SELECT name, mobile, whatsapp, education, permanent_address, current_address 
        FROM users WHERE username=%s
    """, (username,))
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

    return render_template("profile.html", user_data=user_data)

@main.route('/classes')
def classes():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT c.id, c.name, COUNT(b.id) as batch_count 
        FROM classes c
        LEFT JOIN batches b ON b.class_id = c.id
        GROUP BY c.id
        ORDER BY c.name
    """)
    classes = cursor.fetchall()
    conn.close()
    
    return render_template('classes.html', classes=classes)

@main.route('/batches')
def all_batches():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
        
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT b.*, c.name as class_name, 
               (SELECT COUNT(*) FROM students WHERE batch_id = b.id) as student_count
        FROM batches b
        JOIN classes c ON b.class_id = c.id
        ORDER BY c.name, b.start_date
    """)
    batches = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM classes ORDER BY name")
    classes = cursor.fetchall()
    
    conn.close()
    
    return render_template("batches.html",
                         batches=batches,
                         classes=classes,
                         all_batches_view=True)

@main.route('/batches/<int:class_id>', methods=['GET', 'POST'])
def batches(class_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM classes WHERE id = %s", (class_id,))
    class_data = cursor.fetchone()
    
    if not class_data:
        conn.close()
        abort(404)
    
    if request.method == 'POST':
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
        flash('Batch created successfully!', 'success')
        return redirect(url_for('main.batches', class_id=class_id))
    
    cursor.execute("""
        SELECT b.*, COUNT(s.id) as student_count
        FROM batches b
        LEFT JOIN students s ON s.batch_id = b.id
        WHERE b.class_id = %s
        GROUP BY b.id
        ORDER BY b.start_date
    """, (class_id,))
    batches = cursor.fetchall()
    
    conn.close()
    
    return render_template("batches.html",
                         class_data=class_data,
                         batches=batches)

@main.route('/edit_batch/<int:batch_id>', methods=['GET', 'POST'])
def edit_batch(batch_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        batch_name = request.form['batch_name']
        day = request.form['day']
        start_date = request.form['start_date']
        time_slot = request.form['time_slot']
        notes = request.form.get('notes', '')
        class_id = request.form['class_id']
        
        cursor.execute(
            "UPDATE batches SET name = %s, day = %s, start_date = %s, time_slot = %s, notes = %s WHERE id = %s",
            (batch_name, day, start_date, time_slot, notes, batch_id)
        )
        conn.commit()
        conn.close()
        
        flash('Batch updated successfully!', 'success')
        return redirect(url_for('main.batches', class_id=class_id))
    
    cursor.execute("SELECT * FROM batches WHERE id = %s", (batch_id,))
    batch = cursor.fetchone()
    
    cursor.execute("SELECT id, name FROM classes WHERE id = %s", (batch['class_id'],))
    class_data = cursor.fetchone()
    
    conn.close()
    
    if not batch:
        abort(404)
    
    return render_template("edit_batch.html",
                         batch=batch,
                         class_data=class_data)

@main.route('/delete_batch/<int:batch_id>', methods=['POST'])
def delete_batch(batch_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT class_id FROM batches WHERE id = %s", (batch_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        abort(404)
    
    class_id = result['class_id']
    
    cursor.execute("DELETE FROM batches WHERE id = %s", (batch_id,))
    conn.commit()
    conn.close()
    
    flash('Batch deleted successfully!', 'success')
    return redirect(url_for('main.batches', class_id=class_id))

@main.route('/students', methods=["GET", "POST"])
def students():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        class_id = request.form['class_id']
        cursor.execute(
            "INSERT INTO students (name, email, class_id) VALUES (%s, %s, %s)",
            (name, email, class_id)
        )
        conn.commit()

    cursor.execute("""
        SELECT students.id, students.name, students.email, classes.name as class_name 
        FROM students JOIN classes ON students.class_id = classes.id
    """)
    data = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM classes ORDER BY name")
    classes = cursor.fetchall()
    
    conn.close()
    return render_template("students.html", students=data, classes=classes)

@main.route('/placed-students')
def placed_students():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template("placed_students.html")

@main.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))

@main.route('/about')
def about():
    return render_template("about.html")

@main.route('/contact')
def contact():
    return render_template("contact.html")