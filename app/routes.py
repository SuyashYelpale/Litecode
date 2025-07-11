from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from app.models import get_db
from flask import abort
from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField
from wtforms.validators import DataRequired

main = Blueprint("main", __name__)

class ClassForm(FlaskForm):
    class_name = StringField('Class Name', validators=[DataRequired()])
    class_id = HiddenField('Class ID')

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
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT c.id, c.name, 
                   COUNT(DISTINCT b.id) as batch_count,
                   COUNT(DISTINCT s.id) as student_count
            FROM classes c
            LEFT JOIN batches b ON b.class_id = c.id
            LEFT JOIN students s ON s.class_id = c.id
            GROUP BY c.id
            ORDER BY c.name
        """)
        classes = cursor.fetchall()
        
        form = ClassForm()
        return render_template('classes.html', classes=classes, form=form)
        
    except Exception as e:
        flash('Error loading classes: ' + str(e), 'danger')
        return render_template('classes.html', classes=[], form=ClassForm())
    finally:
        if conn:
            conn.close()

@main.route('/add_class', methods=['POST'])
def add_class():
    form = ClassForm()
    if form.validate_on_submit():
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO classes (name) VALUES (%s)", (form.class_name.data,))
            conn.commit()
            flash('Class added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error adding class: ' + str(e), 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/edit_class', methods=['POST'])
def edit_class():
    form = ClassForm()
    if form.validate_on_submit():
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE classes SET name = %s WHERE id = %s", 
                          (form.class_name.data, form.class_id.data))
            conn.commit()
            flash('Class updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error updating class: ' + str(e), 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/delete_class', methods=['POST'])
def delete_class():
    class_id = request.form.get('class_id')
    if class_id:
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM batches WHERE class_id = %s", (class_id,))
            if cursor.fetchone()[0] > 0:
                flash('Cannot delete class with existing batches', 'danger')
                return redirect(url_for('main.classes'))
                
            cursor.execute("DELETE FROM classes WHERE id = %s", (class_id,))
            conn.commit()
            flash('Class deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash('Error deleting class: ' + str(e), 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/classes/<int:class_id>/batches')
def view_class_batches(class_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get the class details
        cursor.execute("SELECT id, name FROM classes WHERE id = %s", (class_id,))
        class_info = cursor.fetchone()
        
        if not class_info:
            flash('Class not found', 'danger')
            return redirect(url_for('main.classes'))
        
        # Get batches for this class with student counts
        cursor.execute("""
            SELECT b.id, b.name, 
                   COUNT(s.id) as student_count
            FROM batches b
            LEFT JOIN students s ON s.batch_id = b.id
            WHERE b.class_id = %s
            GROUP BY b.id
            ORDER BY b.name
        """, (class_id,))
        batches = cursor.fetchall()
        
        return render_template('batches.html',
                            class_info=class_info,  # Pass class info
                            batches=batches)
        
    except Exception as e:
        flash(f'Error loading batches: {str(e)}', 'danger')
        return redirect(url_for('main.classes'))
    finally:
        if conn:
            conn.close()

@main.route('/batches')
def view_all_batches():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get all batches with class names and student counts
        cursor.execute("""
            SELECT b.id, b.name, c.name as class_name, COUNT(s.id) as student_count
            FROM batches b
            JOIN classes c ON b.class_id = c.id
            LEFT JOIN students s ON s.batch_id = b.id
            GROUP BY b.id
            ORDER BY c.name, b.name
        """)
        batches = cursor.fetchall()
        
        return render_template('batches.html', batches=batches)
        
    except Exception as e:
        flash('Error loading batches: ' + str(e), 'danger')
        return redirect(url_for('main.classes'))
    finally:
        if conn:
            conn.close()

@main.route('/students')
def students():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get students with their class and batch names
        cursor.execute("""
            SELECT s.id, s.name, s.email, s.phone, 
                   c.name as class_name, b.name as batch_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN batches b ON s.batch_id = b.id
            ORDER BY s.name
        """)
        students = cursor.fetchall()
        
        # Get classes for the dropdown
        cursor.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cursor.fetchall()
        
        # Get batches for the dropdown
        cursor.execute("SELECT id, name FROM batches ORDER BY name")
        batches = cursor.fetchall()
        
        conn.close()
        
        return render_template('students.html', 
                            students=students, 
                            classes=classes,
                            batches=batches)
        
    except Exception as e:
        print("Database error:", str(e))
        flash("Error loading student data", "danger")
        return render_template('students.html', 
                            students=[], 
                            classes=[],
                            batches=[])

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