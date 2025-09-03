# app.py (Main Flask Application)
from flask import Flask, request, jsonify, session, render_template, redirect, url_for
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
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    if 'user_id' in session:
        if session['role'] == 'admin':
            return redirect(url_for('login'))
        else:
            return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'student')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, hashed_password, role)
            )
            conn.commit()
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            return "Username or email already exists", 400
        finally:
            cur.close()
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            return "Invalid credentials", 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
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
    
    cur.close()
    conn.close()
    
    return render_template('admin_dashboard.html', quizzes=quizzes, users=users)

@app.route('/admin/quiz/new', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        passing_score = int(request.form['passing_score'])
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create quiz
        cur.execute(
            """
            INSERT INTO quizzes (title, description, created_by, passing_score) 
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (title, description, session['user_id'], passing_score)
        )
        quiz_id = cur.fetchone()[0]
        
        # Collect question-related data
        questions = request.form.getlist('question_text')
        question_types = request.form.getlist('question_type')
        options_list = request.form.getlist('options')
        correct_answers = request.form.getlist('correct_answer')
        points_list = request.form.getlist('points')
        
        # Insert questions safely using zip
        for question, q_type, option_str, correct, points in zip(
            questions, question_types, options_list, correct_answers, points_list
        ):
            options = option_str.split('|') if option_str else []
            
            cur.execute(
                """
                INSERT INTO questions 
                (quiz_id, question_text, question_type, options, correct_answer, points) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (quiz_id, question, q_type, json.dumps(options), correct, int(points))
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return redirect(url_for('admin_dashboard'))
    
    return render_template('create_quiz.html')

@app.route('/admin/quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
# ===== QUIZ MANAGEMENT ROUTES =====

@app.route('/admin/quiz/delete/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Find and remove the quiz (replace with your database logic)
    quiz_to_delete = next((q for q in quizzes if q['id'] == quiz_id), None)
    
    if quiz_to_delete:
        # Remove from your data store (replace with your actual data deletion logic)
        quizzes = [q for q in quizzes if q['id'] != quiz_id]
        return jsonify({'message': 'Quiz deleted successfully'}), 200
    else:
        return jsonify({'error': 'Quiz not found'}), 404

@app.route('/admin/quiz/edit/<int:quiz_id>', methods=['POST'])
def edit_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    passing_score = data.get('passing_score')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cur.fetchone()
    if not quiz:
        cur.close()
        conn.close()
        return jsonify({'error': 'Quiz not found'}), 404

    cur.execute(
        "UPDATE quizzes SET title = %s, description = %s, passing_score = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (title, description, passing_score, quiz_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'Quiz updated successfully'}), 200

@app.route('/admin/quiz/get/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Find the quiz using the database
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cur.fetchone()
    cur.close()
    conn.close()
    
    if quiz:
        return jsonify(dict(quiz)), 200
    else:
        return jsonify({'error': 'Quiz not found'}), 404

# ===== USER MANAGEMENT ROUTES =====

@app.route('/admin/user/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Prevent self-deletion
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Find and remove the user (replace with your database logic)
    user_to_delete = next((u for u in users if u['id'] == user_id), None)
    
    if user_to_delete:
        # Remove from your data store (replace with your actual data deletion logic)
        users = [u for u in users if u['id'] != user_id]
        return jsonify({'message': 'User deleted successfully'}), 200
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/admin/user/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    role = data.get('role')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.close()
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    cur.execute(
        "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
        (username, email, role, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'message': 'User updated successfully'}), 200

@app.route('/admin/user/get/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Find the user using the database
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, username, email, role, created_at FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        return jsonify(dict(user)), 200
    else:
        return jsonify({'error': 'User not found'}), 404
    
    # Get quiz details
    cur.execute("SELECT * FROM quizzes WHERE id = %s", (quiz_id,))
    quiz = cur.fetchone()
    
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
    
    cur.close()
    conn.close()
    
    return render_template('student_dashboard.html', quizzes=quizzes, attempts=attempts)

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
        for question in questions:
            selected_answer = request.form.get(f'question_{question["id"]}')
            is_correct = selected_answer == question['correct_answer']
            
            if is_correct:
                score += question['points']
            
            total_points += question['points']
            
            user_answers.append({
                'question_id': question['id'],
                'selected_answer': selected_answer,
                'is_correct': is_correct
            })
        
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)