import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Subject, Enrolment, Assignment, Submission, Resource

app = Flask(__name__)
app.config['SECRET_KEY'] = 'studysphere-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studysphere.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_initial_data():
    if User.query.first():
        return
    prof = User(full_name='Dr. Arvind Kumar', email='prof@snu.edu',
                password_hash=generate_password_hash('pass123'), role='professor')
    stud = User(full_name='Sailesh Kumaran M', email='student@snu.edu',
                password_hash=generate_password_hash('pass123'), role='student',
                reg_number='SNU2026IT104', semester=1, target_cgpa=8.5)
    db.session.add_all([prof, stud])
    db.session.commit()

    sub1 = Subject(code='IT101', name='Data Structures & Algorithms', credits=4,
                   semester=1, department='IT', professor_id=prof.id)
    sub2 = Subject(code='MA102', name='Discrete Mathematics', credits=4,
                   semester=1, department='IT', professor_id=prof.id)
    db.session.add_all([sub1, sub2])
    db.session.commit()

    db.session.add(Enrolment(student_id=stud.id, subject_id=sub1.id, internal_marks=36, grade_point=9.0))
    db.session.add(Enrolment(student_id=stud.id, subject_id=sub2.id, internal_marks=32, grade_point=8.0))
    db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Calculate dynamic CGPA from enrolments
    enrolments = Enrolment.query.filter_by(student_id=current_user.id).all()
    total_credits = sum(Subject.query.get(e.subject_id).credits for e in enrolments) or 1
    weighted_pts = sum(e.grade_point * Subject.query.get(e.subject_id).credits for e in enrolments)
    current_cgpa = round(weighted_pts / total_credits, 2) if enrolments else 8.25

    # Target CGPA Predictor math
    remaining_credits = 20
    req_sgpa = round(((current_user.target_cgpa * (total_credits + remaining_credits)) - weighted_pts) / remaining_credits, 2)

    tasks = [
        {'title': 'Binary Search Tree Lab', 'subject_name': 'Data Structures', 'progress': 75, 'status': 'In Progress', 'deadline': 'Nov 20'},
        {'title': 'Graph Theory Problem Set', 'subject_name': 'Discrete Math', 'progress': 100, 'status': 'Submitted', 'deadline': 'Nov 18'}
    ]
    history = [
        {'icon': 'N', 'title': 'Unit 3 Lecture Notes', 'subtitle': 'Data Structures', 'meta': '2h ago'},
        {'icon': 'G', 'title': 'Quiz 1 Graded: 18/20', 'subtitle': 'Discrete Math', 'meta': 'Yesterday'},
        {'icon': 'A', 'title': 'Attendance Marked: Present', 'subtitle': 'IT101', 'meta': 'Nov 16'}
    ]
    return render_template('student_dash.html', active_page='dashboard',
                           current_cgpa=current_cgpa, attendance_pct=88,
                           required_sgpa=max(0, req_sgpa), tasks=tasks, history=history)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_initial_data()
    app.run(debug=True)