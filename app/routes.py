from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from app.models import get_db
from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField
from wtforms.validators import DataRequired
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from xlsxwriter import Workbook
from flask import send_file


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


@main.route('/dashboard_data')
def dashboard_data():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Classes data
        cursor.execute("""
            SELECT c.id, c.name, COUNT(s.id) as student_count
            FROM classes c
            LEFT JOIN students s ON s.class_id = c.id
            GROUP BY c.id
            ORDER BY c.name
        """)
        classes = cursor.fetchall()
        
        # Batches data
        cursor.execute("""
            SELECT b.id, b.name, COUNT(s.id) as student_count
            FROM batches b
            LEFT JOIN students s ON s.batch_id = b.id
            GROUP BY b.id
            ORDER BY b.name
            LIMIT 8
        """)
        batches = cursor.fetchall()
        
        # Students over time (last 6 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                COUNT(*) as count
            FROM students
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY month
            ORDER BY month
        """)
        students_over_time = cursor.fetchall()
        
        # Format students over time data for chart
        months = []
        counts = []
        for row in students_over_time:
            months.append(row['month'])
            counts.append(row['count'])
        
        return jsonify({
            'classes': classes,
            'batches': batches,
            'students_over_time': {
                'labels': months,
                'data': counts
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@main.route('/profile', methods=["GET", "POST"])
def profile():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = get_db()
    cursor = conn.cursor()
    username = session['user']

    if request.method == "POST":
        try:
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
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')

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
    } if result else None

    return render_template("profile.html", user_data=user_data)

@main.route('/classes')
def classes():
    conn = None
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
        
        return render_template('classes.html', classes=classes, form=ClassForm())
        
    except Exception as e:
        flash(f'Error loading classes: {str(e)}', 'danger')
        return render_template('classes.html', classes=[], form=ClassForm())
    finally:
        if conn:
            conn.close()

@main.route('/add_class', methods=['POST'])
def add_class():
    form = ClassForm()
    if form.validate_on_submit():
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO classes (name) VALUES (%s)", (form.class_name.data,))
            conn.commit()
            flash('Class added successfully!', 'success')
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error adding class: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/edit_class', methods=['POST'])
def edit_class():
    form = ClassForm()
    if form.validate_on_submit():
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE classes SET name = %s WHERE id = %s", 
                         (form.class_name.data, form.class_id.data))
            conn.commit()
            flash('Class updated successfully!', 'success')
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f'Error updating class: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/delete_class', methods=['POST'])
def delete_class():
    class_id = request.form.get('class_id')
    if class_id:
        conn = None
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
            if conn:
                conn.rollback()
            flash(f'Error deleting class: {str(e)}', 'danger')
        finally:
            if conn:
                conn.close()
    return redirect(url_for('main.classes'))

@main.route('/classes/<int:class_id>/batches')
def view_class_batches(class_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, name FROM classes WHERE id = %s", (class_id,))
        class_data = cursor.fetchone()
        
        if not class_data:
            flash('Class not found', 'danger')
            return redirect(url_for('main.classes'))
        
        cursor.execute("""
            SELECT b.id, b.name, b.day, b.start_date, b.time_slot,
                   COUNT(s.id) as student_count
            FROM batches b
            LEFT JOIN students s ON s.batch_id = b.id
            WHERE b.class_id = %s
            GROUP BY b.id
            ORDER BY b.name
        """, (class_id,))
        batches = cursor.fetchall()
        
        return render_template('batches.html',
                            batches=batches,
                            class_data=class_data,
                            all_batches_view=False)
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('main.classes'))
    finally:
        if conn:
            conn.close()

@main.route('/batches')
def view_all_batches():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT b.id, b.name, c.name as class_name, COUNT(s.id) as student_count,
                   b.day, b.start_date, b.time_slot
            FROM batches b
            JOIN classes c ON b.class_id = c.id
            LEFT JOIN students s ON s.batch_id = b.id
            GROUP BY b.id
            ORDER BY c.name, b.name
        """)
        batches = cursor.fetchall()
        
        cursor.execute("SELECT id, name FROM classes ORDER BY name")
        classes = cursor.fetchall()
        
        return render_template('batches.html',
                            batches=batches,
                            classes=classes,
                            all_batches_view=True)
        
    except Exception as e:
        flash(f'Error loading batches: {str(e)}', 'danger')
        return redirect(url_for('main.classes'))
    finally:
        if conn:
            conn.close()

@main.route('/add_batch', methods=['POST'])
def add_batch():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    class_id = request.form['class_id']
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO batches (class_id, name, day, start_date, time_slot, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            class_id,
            request.form['batch_name'],
            request.form['day'],
            request.form['start_date'],
            request.form['time_slot'],
            request.form.get('notes', '')
        ))
        conn.commit()
        flash('Batch added successfully!', 'success')
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error adding batch: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.view_class_batches', class_id=class_id))

@main.route('/edit_batch/<int:batch_id>', methods=['GET', 'POST'])
def edit_batch(batch_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            cursor.execute("""
                UPDATE batches SET
                    name = %s,
                    day = %s,
                    start_date = %s,
                    time_slot = %s,
                    notes = %s
                WHERE id = %s
            """, (
                request.form['batch_name'],
                request.form['day'],
                request.form['start_date'],
                request.form['time_slot'],
                request.form.get('notes', ''),
                batch_id
            ))
            conn.commit()
            flash('Batch updated successfully!', 'success')
            return redirect(request.referrer or url_for('main.view_all_batches'))
        
        cursor.execute("SELECT * FROM batches WHERE id = %s", (batch_id,))
        batch = cursor.fetchone()
        
        if not batch:
            flash('Batch not found', 'danger')
            return redirect(url_for('main.view_all_batches'))
            
        return render_template('edit_batch.html', batch=batch)
        
    except Exception as e:
        flash(f'Error updating batch: {str(e)}', 'danger')
        return redirect(url_for('main.view_all_batches'))
    finally:
        if conn:
            conn.close()

@main.route('/delete_batch/<int:batch_id>', methods=['POST'])
def delete_batch(batch_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE batch_id = %s", (batch_id,))
        if cursor.fetchone()[0] > 0:
            flash('Cannot delete batch with students', 'danger')
            return redirect(request.referrer or url_for('main.view_all_batches'))
            
        cursor.execute("DELETE FROM batches WHERE id = %s", (batch_id,))
        conn.commit()
        flash('Batch deleted successfully', 'success')
        
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error deleting batch: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(request.referrer or url_for('main.view_all_batches'))

@main.route('/batch_students/<int:batch_id>')
def batch_students(batch_id):
    """Get students in a specific batch"""
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT s.id, s.name, s.email, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.batch_id = %s
            ORDER BY s.name
        """, (batch_id,))
        
        students = cursor.fetchall()
        return jsonify(students)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@main.route('/export_batch_students/<int:batch_id>')
def export_batch_students(batch_id):
    """Export batch students to Excel or PDF"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    export_format = request.args.get('format', 'excel')
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get batch info
        cursor.execute("""
            SELECT b.name as batch_name, b.day, b.time_slot, c.name as class_name
            FROM batches b
            LEFT JOIN classes c ON b.class_id = c.id
            WHERE b.id = %s
        """, (batch_id,))
        batch_info = cursor.fetchone()
        
        # Get students
        cursor.execute("""
            SELECT s.name, s.email, c.name as class_name
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.batch_id = %s
            ORDER BY s.name
        """, (batch_id,))
        students = cursor.fetchall()
        
        if export_format == 'excel':
            # Create Excel file
            output = io.BytesIO()
            workbook = Workbook(output)
            worksheet = workbook.add_worksheet()
            
            # Add headers
            headers = ['#', 'Student Name', 'Email', 'Class']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header)
            
            # Add data
            for row, student in enumerate(students, start=1):
                worksheet.write(row, 0, row)
                worksheet.write(row, 1, student['name'])
                worksheet.write(row, 2, student['email'] or 'N/A')
                worksheet.write(row, 3, student['class_name'] or 'N/A')
            
            workbook.close()
            output.seek(0)
            
            filename = f"{batch_info['batch_name']}_students.xlsx"
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
            
        elif export_format == 'pdf':
            # Create PDF file
            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter)
            
            # Create elements
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            title = f"{batch_info['batch_name']} Students"
            elements.append(Paragraph(title, styles['Title']))
            
            # Add batch info
            info_text = f"Class: {batch_info['class_name']} | Day: {batch_info['day']} | Time: {batch_info['time_slot']}"
            elements.append(Paragraph(info_text, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            # Create table data
            data = [['#', 'Student Name', 'Email', 'Class']]
            for i, student in enumerate(students, start=1):
                data.append([
                    str(i),
                    student['name'],
                    student['email'] or 'N/A',
                    student['class_name'] or 'N/A'
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            
            # Build PDF
            pdf.build(elements)
            buffer.seek(0)
            
            filename = f"{batch_info['batch_name']}_students.pdf"
            return send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
            
        else:
            flash('Invalid export format', 'danger')
            return redirect(url_for('main.view_all_batches'))
            
    except Exception as e:
        flash(f'Error exporting students: {str(e)}', 'danger')
        return redirect(url_for('main.view_all_batches'))
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
        
        # Modified query to include mobile and age fields
        cursor.execute("""
            SELECT s.id, s.name, s.email, s.mobile, s.age, s.class_id, s.batch_id,
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
        
        # Get batches with their class names for the dropdown
        cursor.execute("""
            SELECT b.id, b.name, b.class_id, c.name as class_name
            FROM batches b
            JOIN classes c ON b.class_id = c.id
            ORDER BY c.name, b.name
        """)
        batches = cursor.fetchall()
        
        return render_template('students.html', 
                            students=students, 
                            classes=classes,
                            batches=batches)
        
    except Exception as e:
        flash(f"Error loading student data: {str(e)}", "danger")
        return render_template('students.html', 
                            students=[], 
                            classes=[],
                            batches=[])
    finally:
        if conn:
            conn.close()


@main.route('/add_student', methods=['POST'])
def add_student():
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all form data including new fields
        name = request.form['name']
        email = request.form['email']
        class_id = request.form['class_id']
        mobile = request.form.get('mobile')  # Changed to get raw value
        age = request.form.get('age')        # Changed to get raw value
        
        # Convert age to integer if provided, else None
        age = int(age) if age and age.isdigit() else None
        
        cursor.execute("""
            INSERT INTO students (name, email, class_id, mobile, age)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, class_id, mobile, age))
        conn.commit()
        flash('Student added successfully!', 'success')
    except ValueError:
        conn.rollback()
        flash('Please enter a valid age number', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error adding student: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.students'))


@main.route('/edit_student/<int:student_id>', methods=['POST'])
def edit_student(student_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all form data including new fields
        name = request.form['name']
        email = request.form['email']
        class_id = request.form['class_id']
        mobile = request.form.get('mobile')  # Changed to get raw value
        age = request.form.get('age')       # Changed to get raw value
        
        # Convert age to integer if provided, else None
        age = int(age) if age and age.isdigit() else None
        
        cursor.execute("""
            UPDATE students SET
                name = %s,
                email = %s,
                class_id = %s,
                mobile = %s,
                age = %s
            WHERE id = %s
        """, (name, email, class_id, mobile, age, student_id))
        conn.commit()
        flash('Student updated successfully!', 'success')
    except ValueError:
        conn.rollback()
        flash('Please enter a valid age number', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating student: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.students'))


@main.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.students'))



@main.route('/assign_batch/<int:student_id>', methods=['POST'])
def assign_batch(student_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        batch_id = request.form['batch_id']
        
        # Update student's batch
        cursor.execute("""
            UPDATE students 
            SET batch_id = %s 
            WHERE id = %s
        """, (batch_id, student_id))
        
        conn.commit()
        flash('Batch assigned successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error assigning batch: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.students'))


@main.route('/change_batch/<int:student_id>', methods=['POST'])
def change_batch(student_id):
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        batch_id = request.form['batch_id']
        
        # Update student's batch
        cursor.execute("""
            UPDATE students 
            SET batch_id = %s 
            WHERE id = %s
        """, (batch_id, student_id))
        
        conn.commit()
        flash('Batch changed successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error changing batch: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.students'))            

@main.route('/placed-students')
def placed_students():
    """Display all placed students with their details"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get placed students with their details
        cursor.execute("""
            SELECT 
                ps.id as placement_id,
                ps.*, 
                s.id as student_id,
                s.name, 
                s.email, 
                c.name as class_name
            FROM placed_students ps
            JOIN students s ON ps.student_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            ORDER BY ps.created_at DESC
        """)
        placed_students = cursor.fetchall()
        
        return render_template("placed_students.html", 
                            placed_students=placed_students,
                            title="Placed Students")
        
    except Exception as e:
        flash(f'Error loading placed students: {str(e)}', 'danger')
        return render_template("placed_students.html", 
                            placed_students=[],
                            title="Placed Students")
    finally:
        if conn:
            conn.close()

@main.route('/add_placement', methods=['POST'])
def add_placement():
    """Add a new student placement record"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get form data
        student_id = request.form.get('student_id')
        company = request.form.get('company')
        package = request.form.get('package')
        joining_date = request.form.get('joining_date')

        # Validate required fields
        if not all([student_id, company, package, joining_date]):
            flash('All fields are required!', 'warning')
            return redirect(url_for('main.placed_students'))

        # Check if student exists
        cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
        if not cursor.fetchone():
            flash('Student not found!', 'danger')
            return redirect(url_for('main.placed_students'))

        # Check if already placed
        cursor.execute("SELECT 1 FROM placed_students WHERE student_id = %s", (student_id,))
        if cursor.fetchone():
            flash('This student is already placed!', 'warning')
            return redirect(url_for('main.placed_students'))

        # Insert new placement
        cursor.execute("""
            INSERT INTO placed_students 
            (student_id, company, package, joining_date)
            VALUES (%s, %s, %s, %s)
        """, (student_id, company, package, joining_date))
        
        conn.commit()
        flash('Placement added successfully!', 'success')

    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error adding placement: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.placed_students'))

@main.route('/update_placement', methods=['POST'])
def update_placement():
    """Update an existing placement record"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get form data
        placement_id = request.form.get('placement_id')
        student_id = request.form.get('student_id')
        company = request.form.get('company')
        package = request.form.get('package')
        joining_date = request.form.get('joining_date')

        # Validate required fields
        if not all([placement_id, student_id, company, package, joining_date]):
            flash('All fields are required!', 'warning')
            return redirect(url_for('main.placed_students'))

        # Update placement
        cursor.execute("""
            UPDATE placed_students 
            SET 
                company = %s,
                package = %s,
                joining_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND student_id = %s
        """, (company, package, joining_date, placement_id, student_id))
        
        # Check if any row was affected
        if cursor.rowcount == 0:
            flash('No placement found to update!', 'warning')
        else:
            conn.commit()
            flash('Placement updated successfully!', 'success')
            
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error updating placement: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.placed_students'))

@main.route('/remove_placement', methods=['POST'])
def remove_placement():
    """Delete a placement record"""
    if 'user' not in session:
        return redirect(url_for('auth.login'))

    placement_id = request.form.get('placement_id')
    if not placement_id:
        flash('No placement specified', 'danger')
        return redirect(url_for('main.placed_students'))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Delete placement
        cursor.execute("DELETE FROM placed_students WHERE id = %s", (placement_id,))
        
        # Check if any row was affected
        if cursor.rowcount == 0:
            flash('No placement found to delete!', 'warning')
        else:
            conn.commit()
            flash('Placement removed successfully!', 'success')
            
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f'Error removing placement: {str(e)}', 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('main.placed_students'))

@main.route('/search_students')
def search_students():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT s.id, s.name, c.name as class_name, s.email
            FROM students s
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.name LIKE %s AND s.id NOT IN (
                SELECT student_id FROM placed_students
            )
            LIMIT 10
        """, (f'%{query}%',))
        
        results = cursor.fetchall()
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if conn:
            conn.close()

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