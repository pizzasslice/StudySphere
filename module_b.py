from datetime import date, datetime
from math import ceil, floor

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Attendance, Enrolment, Subject, User, db

module_b = Blueprint('module_b', __name__)

GRADING_SCALE = (
    ('O', 10.0, 90),
    ('A+', 9.0, 80),
    ('A', 8.0, 70),
    ('B+', 7.0, 60),
    ('B', 6.0, 50),
    ('C', 5.0, 40),
    ('F', 0.0, 0),
)
MIN_ATTENDANCE_PCT = 75.0
REMAINING_CREDITS = 20


def marks_to_grade(total_marks):
    for grade, points, minimum in GRADING_SCALE:
        if total_marks >= minimum:
            return grade, points
    return 'F', 0.0


def _student_enrolments():
    if current_user.role == 'student':
        return Enrolment.query.filter_by(student_id=current_user.id).all()
    if current_user.role == 'professor':
        subject_ids = [s.id for s in Subject.query.filter_by(professor_id=current_user.id)]
        if not subject_ids:
            return []
        return Enrolment.query.filter(Enrolment.subject_id.in_(subject_ids)).all()
    abort(403)


@module_b.route('/cgpa', methods=['GET', 'POST'])
@login_required
def cgpa():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_target' and current_user.role == 'student':
            try:
                target = float(request.form.get('target_cgpa', '8.0'))
            except (TypeError, ValueError):
                abort(400)
            if not 0 <= target <= 10:
                abort(400)
            current_user.target_cgpa = target
        elif action == 'save_marks':
            try:
                enrolment_id = int(request.form.get('enrolment_id', ''))
                internal = float(request.form.get('internal_marks', '0'))
                external = float(request.form.get('external_marks', '0'))
            except (TypeError, ValueError):
                abort(400)
            enrolment = Enrolment.query.get_or_404(enrolment_id)
            subject = Subject.query.get_or_404(enrolment.subject_id)
            allowed = (
                current_user.role == 'student' and enrolment.student_id == current_user.id
            ) or (
                current_user.role == 'professor' and subject.professor_id == current_user.id
            )
            if not allowed:
                abort(403)
            if not 0 <= internal <= subject.internal_weight or not 0 <= external <= subject.external_weight:
                abort(400)
            enrolment.internal_marks = internal
            enrolment.external_marks = external
            enrolment.grade_point = marks_to_grade(internal + external)[1]
        else:
            abort(400)
        db.session.commit()
        flash('Your academic target was updated.' if action == 'update_target' else 'Marks were updated.')
        return redirect(url_for('module_b.cgpa'))

    rows = []
    total_credits = 0
    weighted_points = 0.0
    for enrolment in _student_enrolments():
        subject = db.session.get(Subject, enrolment.subject_id)
        if subject is None:
            continue
        credits = subject.credits or 0
        total_credits += credits
        weighted_points += (enrolment.grade_point or 0) * credits
        internal = enrolment.internal_marks or 0
        external = enrolment.external_marks or 0
        rows.append({
            'enrol': enrolment,
            'subject': subject,
            'grade_letter': marks_to_grade(internal + external)[0],
            'req_for_aplus': max(0, ceil(80 - internal)) if 80 - internal <= subject.external_weight else 'Impossible',
            'req_for_o': max(0, ceil(90 - internal)) if 90 - internal <= subject.external_weight else 'Impossible',
        })

    current_cgpa = round(weighted_points / total_credits, 2) if total_credits else 0.0
    target_cgpa = current_user.target_cgpa or 8.0
    required_sgpa = (
        (target_cgpa * (total_credits + REMAINING_CREDITS) - weighted_points)
        / REMAINING_CREDITS
    )
    return render_template(
        'cgpa.html', active_page='cgpa', subject_rows=rows,
        current_cgpa=current_cgpa, target_cgpa=target_cgpa,
        total_credits=total_credits, remaining_credits=REMAINING_CREDITS,
        req_avg_sgpa=max(0.0, round(required_sgpa, 2)),
        is_achievable=required_sgpa <= 10, grading_scale=GRADING_SCALE,
    )


