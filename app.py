import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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
from module_c import module_c

# ---------------- FLASK APPLICATION ----------------

app = Flask(__name__)

app.config['SECRET_KEY'] = 'studysphere-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///studysphere.db'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register Person 2 & Person 3 blueprints
app.register_blueprint(module_b)
app.register_blueprint(module_c)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ---------------- USER LOADER ----------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------- HELPER & INITIAL DATABASE DATA ----------------

def save_uploaded_file(file_obj):
    if file_obj and file_obj.filename:
        clean_name = f"{int(datetime.utcnow().timestamp())}_{secure_filename(file_obj.filename)}"
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], clean_name))
        return clean_name
    return None


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

    db.session.add(Enrolment(student_id=stud.id, subject_id=sub1.id, internal_marks=36, grade_point=9.0))
    db.session.add(Enrolment(student_id=stud.id, subject_id=sub2.id, internal_marks=32, grade_point=8.0))
    db.session.add(Assignment(
        subject_id=sub1.id,
        title='Binary Search Tree Lab',
        instructions='Implement insertion, deletion, and inorder traversal in Python and upload your PDF report.',
        max_marks=50,
        deadline=datetime(2026, 11, 25, 23, 59)
    ))
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


# ---------------- DASHBOARD (PROFESSOR & STUDENT) ----------------

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'professor':
        subjects = Subject.query.filter_by(professor_id=current_user.id).all()
        sub_ids = [s.id for s in subjects]
        assignments = Assignment.query.filter(Assignment.subject_id.in_(sub_ids)).all() if sub_ids else []
        assign_ids = [a.id for a in assignments]
        subs = Submission.query.filter(Submission.assignment_id.in_(assign_ids)).all() if assign_ids else []
        pending_count = sum(1 for s in subs if s.status != 'Graded')
        recent_subs = [(s, Assignment.query.get(s.assignment_id), User.query.get(s.student_id)) for s in subs[:5]]
        return render_template(
            'prof_dash.html',
            active_page='dashboard',
            subjects=subjects,
            assignments=assignments,
            pending_count=pending_count,
            recent_subs=recent_subs
        )

    enrolments = Enrolment.query.filter_by(student_id=current_user.id).all()
    total_credits = 0
    weighted_points = 0

    for enrolment in enrolments:
        subject = db.session.get(Subject, enrolment.subject_id)
        if subject:
            credits = subject.credits or 0
            grade_point = enrolment.grade_point or 0
            total_credits += credits
            weighted_points += grade_point * credits

    current_cgpa = round(weighted_points / total_credits, 2) if total_credits > 0 else 8.25

    # CGPA target prediction
    target_cgpa = current_user.target_cgpa or 8.0
    remaining_credits = 20
    required_sgpa = (
        round(((target_cgpa * (total_credits + remaining_credits)) - weighted_points) / remaining_credits, 2)
        if remaining_credits > 0 else 0
    )

    # Actual attendance percentage
    attendance_records = Attendance.query.filter_by(student_id=current_user.id).all()
    total_classes = len(attendance_records)
    present_classes = sum(
        1 for record in attendance_records
        if record.status and record.status.lower() == 'present'
    )
    attendance_pct = round((present_classes / total_classes) * 100, 1) if total_classes > 0 else 100.0

    # Live assignment tasks
    sub_ids = [e.subject_id for e in enrolments]
    real_assigns = Assignment.query.filter(Assignment.subject_id.in_(sub_ids)).all() if sub_ids else []
    tasks = []
    for a in real_assigns[:4]:
        sub_obj = db.session.get(Subject, a.subject_id)
        submitted = Submission.query.filter_by(assignment_id=a.id, student_id=current_user.id).first()
        tasks.append({
            'title': a.title,
            'subject_name': sub_obj.name if sub_obj else 'Subject',
            'progress': 100 if submitted else 35,
            'status': submitted.status if submitted else 'Pending',
            'deadline': a.deadline.strftime('%b %d')
        })

    history = [
        {'icon': 'N', 'title': 'Check Subjects & Notes', 'subtitle': 'Course Materials', 'meta': 'Live'},
        {'icon': 'A', 'title': f'{len(real_assigns)} Active Tasks', 'subtitle': 'Assignments Tab', 'meta': 'Synced'}
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


# ---------------- SUBJECTS & NOTES ----------------

@app.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_subject' and current_user.role == 'professor':
            new_sub = Subject(
                code=request.form['code'].upper(),
                name=request.form['name'],
                credits=int(request.form['credits']),
                department=current_user.department,
                internal_weight=int(request.form.get('internal_weight', 40)),
                external_weight=int(request.form.get('external_weight', 60)),
                professor_id=current_user.id
            )
            db.session.add(new_sub)
            db.session.commit()
        elif action == 'upload_note' and current_user.role == 'professor':
            filename = save_uploaded_file(request.files.get('note_file'))
            if filename:
                db.session.add(Resource(
                    subject_id=int(request.form['subject_id']),
                    title=request.form['title'],
                    topic=request.form.get('topic'),
                    file_path=filename
                ))
                db.session.commit()
        elif action == 'enrol' and current_user.role == 'student':
            sub_id = int(request.form['subject_id'])
            if not Enrolment.query.filter_by(student_id=current_user.id, subject_id=sub_id).first():
                db.session.add(Enrolment(student_id=current_user.id, subject_id=sub_id))
                db.session.commit()
        return redirect(url_for('subjects'))

    all_subjects = Subject.query.all()
    resources = Resource.query.order_by(Resource.uploaded_at.desc()).all()
    enrolled_ids = [e.subject_id for e in Enrolment.query.filter_by(student_id=current_user.id).all()]
    return render_template(
        'subjects.html',
        active_page='subjects',
        subjects=all_subjects,
        resources=resources,
        enrolled_ids=enrolled_ids
    )


# ---------------- ASSIGNMENTS & GRADING ----------------

@app.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_assignment' and current_user.role == 'professor':
            ref_file = save_uploaded_file(request.files.get('ref_file'))
            deadline_dt = datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M')
            db.session.add(Assignment(
                subject_id=int(request.form['subject_id']),
                title=request.form['title'],
                instructions=request.form['instructions'],
                max_marks=int(request.form['max_marks']),
                deadline=deadline_dt,
                reference_file=ref_file
            ))
            db.session.commit()
        elif action == 'submit_work' and current_user.role == 'student':
            sub_file = save_uploaded_file(request.files.get('submission_file'))
            assign_id = int(request.form['assignment_id'])
            if sub_file:
                existing = Submission.query.filter_by(assignment_id=assign_id, student_id=current_user.id).first()
                if existing:
                    existing.file_path = sub_file
                    existing.submitted_at = datetime.utcnow()
                    existing.status = 'Submitted'
                else:
                    db.session.add(Submission(assignment_id=assign_id, student_id=current_user.id, file_path=sub_file))
                db.session.commit()
        elif action == 'grade_sub' and current_user.role == 'professor':
            sub_obj = Submission.query.get(int(request.form['submission_id']))
            if sub_obj:
                sub_obj.marks_awarded = float(request.form['marks'])
                sub_obj.feedback = request.form.get('feedback', '')
                sub_obj.status = 'Graded'
                db.session.commit()
        return redirect(url_for('assignments'))

    subjects_list = Subject.query.all()
    if current_user.role == 'student':
        enrolled_ids = [e.subject_id for e in Enrolment.query.filter_by(student_id=current_user.id).all()]
        assigns = Assignment.query.filter(Assignment.subject_id.in_(enrolled_ids)).all() if enrolled_ids else []
    else:
        assigns = Assignment.query.all()

    assignment_rows = [(a, Subject.query.get(a.subject_id)) for a in assigns]
    student_subs = {s.assignment_id: s for s in Submission.query.filter_by(student_id=current_user.id).all()}
    all_subs = Submission.query.all()
    user_map = {u.id: u for u in User.query.all()}

    return render_template(
        'assignments.html',
        active_page='assignments',
        subjects=subjects_list,
        assignment_rows=assignment_rows,
        student_subs=student_subs,
        all_subs=all_subs,
        user_map=user_map
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

with app.app_context():
    db.create_all()
    seed_initial_data()

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)