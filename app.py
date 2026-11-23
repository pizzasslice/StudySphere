
import os

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db,
    User,
    Subject,
    Enrolment,
    Assignment,
    Submission,
    Resource,
    Attendance
)

from module_b import module_b


# ---------------- FLASK APPLICATION ----------------

app = Flask(__name__)

app.config['SECRET_KEY'] = 'studysphere-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studysphere.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Register Person 2 blueprint
app.register_blueprint(module_b)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------- USER LOADER ----------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- INITIAL DATABASE DATA ----------------

def seed_initial_data():

    if User.query.first():
        return

    prof = User(
        full_name='Dr. Arvind Kumar',
        email='prof@snu.edu',
        password_hash=generate_password_hash('pass123'),
        role='professor'
    )

    stud = User(
        full_name='Sailesh Kumaran M',
        email='student@snu.edu',
        password_hash=generate_password_hash('pass123'),
        role='student',
        reg_number='SNU2026IT104',
        semester=1,
        target_cgpa=8.5
    )

    db.session.add_all([prof, stud])
    db.session.commit()

    sub1 = Subject(
        code='IT101',
        name='Data Structures & Algorithms',
        credits=4,
        semester=1,
        department='IT',
        professor_id=prof.id
    )

    sub2 = Subject(
        code='MA102',
        name='Discrete Mathematics',
        credits=4,
        semester=1,
        department='IT',
        professor_id=prof.id
    )

    db.session.add_all([sub1, sub2])
    db.session.commit()

    enrolment1 = Enrolment(
        student_id=stud.id,
        subject_id=sub1.id,
        internal_marks=36,
        grade_point=9.0
    )

    enrolment2 = Enrolment(
        student_id=stud.id,
        subject_id=sub2.id,
        internal_marks=32,
        grade_point=8.0
    )

    db.session.add_all([enrolment1, enrolment2])
    db.session.commit()


# ---------------- LOGIN ----------------

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid email or password')

    return render_template('login.html')


# ---------------- STUDENT DASHBOARD ----------------

@app.route('/dashboard')
@login_required
def dashboard():

    enrolments = Enrolment.query.filter_by(
        student_id=current_user.id
    ).all()

    total_credits = 0
    weighted_points = 0

    for enrolment in enrolments:

        subject = db.session.get(Subject, enrolment.subject_id)

        if subject:
            credits = subject.credits or 0
            grade_point = enrolment.grade_point or 0

            total_credits += credits
            weighted_points += grade_point * credits

    current_cgpa = (
        round(weighted_points / total_credits, 2)
        if total_credits > 0 else 0
    )

    # CGPA target prediction
    target_cgpa = current_user.target_cgpa or 8.0
    remaining_credits = 20

    required_sgpa = (
        (target_cgpa * (total_credits + remaining_credits)
         - weighted_points) / remaining_credits
        if remaining_credits > 0 else 0
    )

    required_sgpa = round(required_sgpa, 2)

    # Calculate actual attendance percentage
    attendance_records = Attendance.query.filter_by(
        student_id=current_user.id
    ).all()

    total_classes = len(attendance_records)

    present_classes = sum(
        1 for record in attendance_records
        if record.status and record.status.lower() == 'present'
    )

    attendance_pct = (
        round((present_classes / total_classes) * 100, 2)
        if total_classes > 0 else 0
    )

    # Dashboard tasks
    tasks = [
        {
            'title': 'Binary Search Tree Lab',
            'subject_name': 'Data Structures',
            'progress': 75,
            'status': 'In Progress',
            'deadline': 'Nov 20'
        },
        {
            'title': 'Graph Theory Problem Set',
            'subject_name': 'Discrete Math',
            'progress': 100,
            'status': 'Submitted',
            'deadline': 'Nov 18'
        }
    ]

    # Dashboard activity history
    history = [
        {
            'icon': 'N',
            'title': 'Unit 3 Lecture Notes',
            'subtitle': 'Data Structures',
            'meta': '2 hours ago'
        },
        {
            'icon': 'G',
            'title': 'Quiz 1 Graded: 18/20',
            'subtitle': 'Discrete Math',
            'meta': 'Yesterday'
        },
        {
            'icon': 'A',
            'title': 'Attendance Marked: Present',
            'subtitle': 'IT101',
            'meta': 'Nov 16'
        }
    ]

    return render_template(
        'student_dash.html',
        active_page='dashboard',
        current_cgpa=current_cgpa,
        attendance_pct=attendance_pct,
        required_sgpa=max(0, required_sgpa),
        tasks=tasks,
        history=history
    )


# ---------------- LOGOUT ----------------

@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect(url_for('login'))


# ---------------- RUN APPLICATION ----------------

if __name__ == '__main__':

    with app.app_context():
        db.create_all()
        seed_initial_data()

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.run(debug=True)