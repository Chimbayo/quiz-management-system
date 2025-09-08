# app.py (Main Flask Application)
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, flash
from flask_cors import CORS
import psycopg2
import psycopg2.extras
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
bcrypt.init_app(app)
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'
CORS(app)

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'quiz_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn

# Initialize database tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create quizzes table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            created_by INTEGER REFERENCES users(id),
            passing_score INTEGER DEFAULT 60,
            duration_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Ensure duration column exists for older DBs
    try:
        cur.execute("ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 0")
    except Exception:
        pass
    
    # Create questions table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            quiz_id INTEGER REFERENCES quizzes(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            question_type VARCHAR(20) DEFAULT 'multiple_choice',
            options JSONB,
            correct_answer VARCHAR(255) NOT NULL,
            points INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create attempts table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            quiz_id INTEGER REFERENCES quizzes(id),
            score INTEGER,
            passed BOOLEAN,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ensure ON DELETE CASCADE on quiz_attempts.quiz_id (best-effort for existing DBs)
    try:
        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints tc
                    WHERE tc.constraint_name = 'quiz_attempts_quiz_id_fkey'
                      AND tc.table_name = 'quiz_attempts'
                ) THEN
                    ALTER TABLE quiz_attempts DROP CONSTRAINT quiz_attempts_quiz_id_fkey;
                END IF;
            END$$;
        """)
        cur.execute("""
            ALTER TABLE quiz_attempts
            ADD CONSTRAINT quiz_attempts_quiz_id_fkey
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
        """)
    except Exception:
        pass
    
    # Ensure ON DELETE CASCADE on quiz_attempts.user_id (best-effort for existing DBs)
    try:
        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints tc
                    WHERE tc.constraint_name = 'quiz_attempts_user_id_fkey'
                      AND tc.table_name = 'quiz_attempts'
                ) THEN
                    ALTER TABLE quiz_attempts DROP CONSTRAINT quiz_attempts_user_id_fkey;
                END IF;
            END$$;
        """)
        cur.execute("""
            ALTER TABLE quiz_attempts
            ADD CONSTRAINT quiz_attempts_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """)
    except Exception:
        pass
    
    # Create answers table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id SERIAL PRIMARY KEY,
            attempt_id INTEGER REFERENCES quiz_attempts(id) ON DELETE CASCADE,
            question_id INTEGER REFERENCES questions(id),
            selected_answer VARCHAR(255),
            is_correct BOOLEAN
        )
    ''')
    
    # Create admin user if not exists
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if cur.fetchone()[0] == 0:
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        cur.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
            ('admin', 'admin@quiz.com', hashed_password, 'admin')
        )
    
    conn.commit()
    cur.close()
    conn.close()

# Routes
@app.route('/')
def home():
    # Always show login as the landing page
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Enforce student role on self-registration
        role = 'student'
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed_password, role)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('Username or email already exists.', 'error')
            return render_template('register.html')
        finally:
            cur.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        portal = request.form.get('portal', 'student')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # Enforce role based on chosen portal
            if portal == 'admin' and user['role'] != 'admin':
                flash('Invalid portal for this account. Please use the Student portal.', 'error')
                return render_template('login.html')
            if portal == 'student' and user['role'] == 'admin':
                # Allow admin to still choose admin portal instead
                flash('Admin accounts should use the Admin portal.', 'error')
                return render_template('login.html')
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get all quizzes created by this admin
    cur.execute("SELECT * FROM quizzes WHERE created_by = %s ORDER BY created_at DESC", (session['user_id'],))
    quizzes = cur.fetchall()
    
    # Get all users
    cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    
    # Get statistics
    cur.execute("SELECT COUNT(*) FROM quizzes")
    total_quizzes = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM quiz_attempts")
    total_attempts = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         quizzes=quizzes, 
                         users=users, 
                         total_quizzes=total_quizzes,
                         total_students=total_students,
                         total_attempts=total_attempts)

@app.route('/admin/quiz/new', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        passing_score = int(request.form['passing_score'])
        duration_minutes = int(request.form.get('duration_minutes', 0) or 0)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Create quiz
            cur.execute(
                """
                INSERT INTO quizzes (title, description, created_by, passing_score, duration_minutes) 
                VALUES (%s, %s, %s, %s, %s) RETURNING id
                """,
                (title, description, session['user_id'], passing_score, duration_minutes)
            )
            quiz_id = cur.fetchone()[0]
            
            # Collect question-related data
            questions = request.form.getlist('question_text')
            question_types = request.form.getlist('question_type')
            options_list = request.form.getlist('options')
            correct_answers = request.form.getlist('correct_answer')
            points_list = request.form.getlist('points')

            # Insert questions by index to avoid zip truncation
            total = max(len(questions), len(question_types), len(options_list), len(correct_answers), len(points_list))
            for i in range(total):
                question = (questions[i] if i < len(questions) else '').strip()
                if not question:
                    continue
                q_type = question_types[i] if i < len(question_types) else 'multiple_choice'
                option_str = options_list[i] if i < len(options_list) else ''
                correct = correct_answers[i] if i < len(correct_answers) else ''
                points = int(points_list[i]) if i < len(points_list) and points_list[i] else 1

                # Auto-fill options for true/false
                if q_type == 'true_false':
                    options = ['True', 'False']
                else:
                    options = [o.strip() for o in (option_str.split('|') if option_str else []) if o.strip()]

                cur.execute(
                    """
                    INSERT INTO questions 
                    (quiz_id, question_text, question_type, options, correct_answer, points) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (quiz_id, question, q_type, json.dumps(options), correct, points)
                )
            
            conn.commit()
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error creating quiz: {str(e)}', 'error')
            return render_template('create_quiz.html')
        finally:
            cur.close()
            conn.close()
    
    return render_template('create_quiz.html')

@app.route('/quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get quiz details
    cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cur.fetchone()
    
    if quiz is None:
        flash('Quiz not found.', 'error')
        return redirect(url_for('student_dashboard' if session['role'] == 'student' else 'admin_dashboard'))
    
    # Get questions
    cur.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
    questions = cur.fetchall()
    
    # Get attempts
    cur.execute("""
        SELECT u.username, qa.score, qa.passed, qa.attempted_at 
        FROM quiz_attempts qa 
        JOIN users u ON qa.user_id = u.id 
        WHERE qa.quiz_id = %s 
        ORDER BY qa.attempted_at DESC
    """, (quiz_id,))
    attempts = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('view_quiz.html', quiz=quiz, questions=questions, attempts=attempts)

@app.route('/admin/quiz/<int:quiz_id>/attempts.csv')
def export_quiz_attempts_csv(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Ensure admin owns the quiz
        cur.execute("SELECT id, title FROM quizzes WHERE id = %s AND created_by = %s", (quiz_id, session['user_id']))
        quiz = cur.fetchone()
        if not quiz:
            return jsonify({'error': 'Quiz not found or unauthorized'}), 404

        cur.execute(
            """
            SELECT u.username, u.email, qa.score, qa.passed, qa.attempted_at
            FROM quiz_attempts qa
            JOIN users u ON qa.user_id = u.id
            WHERE qa.quiz_id = %s
            ORDER BY qa.attempted_at DESC
            """,
            (quiz_id,)
        )
        rows = cur.fetchall()

        # Build CSV
        import csv
        from io import StringIO
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['Username', 'Email', 'Score (%)', 'Passed', 'Attempted At'])
        for r in rows:
            writer.writerow([r['username'], r['email'], round(r['score'] or 0, 2), 'Yes' if r['passed'] else 'No', r['attempted_at']])

        output = si.getvalue()
        from flask import Response
        filename = f"quiz_{quiz_id}_attempts.csv"
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/quiz/<int:quiz_id>/questions', methods=['GET'])
def get_questions_for_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Ensure quiz belongs to admin
        cur.execute("SELECT id FROM quizzes WHERE id = %s AND created_by = %s", (quiz_id, session['user_id']))
        if not cur.fetchone():
            return jsonify({'error': 'Quiz not found or unauthorized'}), 404

        cur.execute("SELECT id, question_text, question_type, options, correct_answer, points FROM questions WHERE quiz_id = %s ORDER BY id ASC", (quiz_id,))
        questions = cur.fetchall()
        # Convert options JSON to list if needed
        result = []
        for q in questions:
            row = dict(q)
            # If options is stored as JSON text, psycopg2 may return as list already due to JSONB
            if isinstance(row.get('options'), str):
                try:
                    row['options'] = json.loads(row['options'])
                except Exception:
                    row['options'] = []
            result.append(row)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/question/get/<int:question_id>', methods=['GET'])
def get_question(question_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""
            SELECT q.id, q.quiz_id, q.question_text, q.question_type, q.options, q.correct_answer, q.points
            FROM questions q
            JOIN quizzes z ON q.quiz_id = z.id
            WHERE q.id = %s AND z.created_by = %s
        """, (question_id, session['user_id']))
        q = cur.fetchone()
        if not q:
            return jsonify({'error': 'Question not found or unauthorized'}), 404
        row = dict(q)
        if isinstance(row.get('options'), str):
            try:
                row['options'] = json.loads(row['options'])
            except Exception:
                row['options'] = []
        return jsonify(row), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/question/edit/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    question_text = data.get('question_text')
    question_type = data.get('question_type')
    options = data.get('options') or []
    correct_answer = data.get('correct_answer')
    points = data.get('points')

    if not question_text or not correct_answer or not question_type:
        return jsonify({'error': 'Missing required fields'}), 400

    if question_type not in ['multiple_choice', 'true_false']:
        return jsonify({'error': 'Invalid question type'}), 400

    if question_type == 'multiple_choice' and not isinstance(options, list):
        return jsonify({'error': 'Options must be a list for multiple_choice'}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Ensure question belongs to a quiz owned by current admin
        cur.execute("""
            SELECT q.id FROM questions q
            JOIN quizzes z ON q.quiz_id = z.id
            WHERE q.id = %s AND z.created_by = %s
        """, (question_id, session['user_id']))
        if not cur.fetchone():
            return jsonify({'error': 'Question not found or unauthorized'}), 404

        cur.execute(
            """
            UPDATE questions
            SET question_text = %s,
                question_type = %s,
                options = %s,
                correct_answer = %s,
                points = %s
            WHERE id = %s
            """,
            (
                question_text,
                question_type,
                json.dumps(options) if options else json.dumps([]),
                correct_answer,
                int(points) if points is not None else 1,
                question_id
            )
        )
        conn.commit()
        return jsonify({'message': 'Question updated successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/quiz/delete/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if quiz exists and belongs to this admin
        cur.execute("SELECT id FROM quizzes WHERE id = %s AND created_by = %s", (quiz_id, session['user_id']))
        if not cur.fetchone():
            return jsonify({'error': 'Quiz not found or unauthorized'}), 404
        
        # First delete attempts explicitly to avoid FK issues on older schemas
        cur.execute("DELETE FROM quiz_attempts WHERE quiz_id = %s", (quiz_id,))
        # Delete quiz (questions are removed via ON DELETE CASCADE on questions.quiz_id)
        cur.execute("DELETE FROM quizzes WHERE id = %s", (quiz_id,))
        conn.commit()
        
        return jsonify({'message': 'Quiz deleted successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/quiz/delete/<int:quiz_id>', methods=['POST'])
def delete_quiz_post(quiz_id):
    # POST fallback for environments that block DELETE
    return delete_quiz(quiz_id)

@app.route('/admin/quiz/edit/<int:quiz_id>', methods=['POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    passing_score = data.get('passing_score')

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if quiz exists and belongs to this admin
        cur.execute("SELECT id FROM quizzes WHERE id = %s AND created_by = %s", (quiz_id, session['user_id']))
        if not cur.fetchone():
            return jsonify({'error': 'Quiz not found or unauthorized'}), 404

        cur.execute(
            "UPDATE quizzes SET title = %s, description = %s, passing_score = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (title, description, passing_score, quiz_id)
        )
        conn.commit()
        return jsonify({'message': 'Quiz updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/quiz/get/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        cur.execute("SELECT id, title, description, passing_score FROM quizzes WHERE id = %s AND created_by = %s", (quiz_id, session['user_id']))
        quiz = cur.fetchone()
        
        if quiz:
            return jsonify(dict(quiz)), 200
        else:
            return jsonify({'error': 'Quiz not found or unauthorized'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/user/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Prevent self-deletion
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return jsonify({'error': 'User not found'}), 404

        # Delete attempts explicitly first to avoid FK issues on older schemas
        cur.execute("DELETE FROM quiz_attempts WHERE user_id = %s", (user_id,))
        # Delete user (cascade will handle related data on modern schemas)
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
def delete_user_post(user_id):
    # POST fallback for environments that block DELETE
    return delete_user(user_id)

@app.route('/admin/user/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    role = data.get('role')

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            return jsonify({'error': 'User not found'}), 404

        cur.execute(
            "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
            (username, email, role, user_id)
        )
        conn.commit()
        return jsonify({'message': 'User updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/admin/user/get/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        cur.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if user:
            return jsonify(dict(user)), 200
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get all quizzes
    cur.execute("SELECT * FROM quizzes ORDER BY created_at DESC")
    quizzes = cur.fetchall()
    
    # Get user's attempts
    cur.execute("""
        SELECT q.title, qa.score, qa.passed, qa.attempted_at 
        FROM quiz_attempts qa 
        JOIN quizzes q ON qa.quiz_id = q.id 
        WHERE qa.user_id = %s 
        ORDER BY qa.attempted_at DESC
    """, (session['user_id'],))
    attempts = cur.fetchall()
    
    # Get statistics
    cur.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = %s", (session['user_id'],))
    total_attempts = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id = %s AND passed = true", (session['user_id'],))
    passed_attempts = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return render_template('student_dashboard.html', 
                         quizzes=quizzes, 
                         attempts=attempts,
                         total_attempts=total_attempts,
                         passed_attempts=passed_attempts)

@app.route('/quiz/<int:quiz_id>/attempt', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        # Calculate score
        score = 0
        total_points = 0
        
        cur.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
        questions = cur.fetchall()
        
        user_answers = []
        missing_answer = False
        for question in questions:
            selected_answer = request.form.get(f'question_{question["id"]}')
            if selected_answer is None or str(selected_answer).strip() == "":
                missing_answer = True
            is_correct = selected_answer == question['correct_answer']
            
            if is_correct:
                score += question['points']
            
            total_points += question['points']
            
            user_answers.append({
                'question_id': question['id'],
                'selected_answer': selected_answer,
                'is_correct': is_correct
            })

        # Deny submission if any question is unanswered
        if missing_answer:
            flash('Please answer all questions before submitting the quiz.', 'error')
            # Re-render attempt page
            cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
            quiz = cur.fetchone()
            cur.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
            questions = cur.fetchall()
            cur.close()
            conn.close()
            return render_template('attempt_quiz.html', quiz=quiz, questions=questions)

        # Calculate percentage
        percentage = (score / total_points) * 100 if total_points > 0 else 0
        
        # Check if passed
        cur.execute("SELECT passing_score FROM quizzes WHERE id = %s", (quiz_id,))
        passing_score = cur.fetchone()['passing_score']
        passed = percentage >= passing_score
        
        # Save attempt
        cur.execute(
            "INSERT INTO quiz_attempts (user_id, quiz_id, score, passed) VALUES (%s, %s, %s, %s) RETURNING id",
            (session['user_id'], quiz_id, percentage, passed)
        )
        attempt_id = cur.fetchone()[0]
        
        # Save answers
        for answer in user_answers:
            cur.execute(
                "INSERT INTO user_answers (attempt_id, question_id, selected_answer, is_correct) VALUES (%s, %s, %s, %s)",
                (attempt_id, answer['question_id'], answer['selected_answer'], answer['is_correct'])
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return render_template('quiz_result.html', score=percentage, passed=passed, passing_score=passing_score)
    
    # GET request - show quiz
    cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cur.fetchone()
    
    cur.execute("SELECT * FROM questions WHERE quiz_id = %s", (quiz_id,))
    questions = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('attempt_quiz.html', quiz=quiz, questions=questions)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets $PORT
    app.run(host="0.0.0.0", port=port, debug=True)
