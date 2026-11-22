from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Subject, Routine, Assignment

module_c = Blueprint('module_c', __name__)

# Self-contained Module C tables (Zero conflict with models.py)
class ProjectGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    members_list = db.Column(db.String(255), default='')

class GroupTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('project_group.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    assigned_to = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.String(50), nullable=False)
    is_done = db.Column(db.Boolean, default=False)

class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ForumReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@module_c.route('/routines', methods=['GET', 'POST'])
@login_required
def routines_tracker():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_routine':
            db.session.add(Routine(
                user_id=current_user.id,
                title=request.form['title'],
                category=request.form.get('category', 'Study'),
                time_slot=request.form['time_slot']
            ))
            db.session.commit()
        elif action == 'toggle_routine':
            r = Routine.query.get(int(request.form['routine_id']))
            if r and r.user_id == current_user.id:
                r.is_completed = not r.is_completed
                db.session.commit()
        elif action == 'delete_routine':
            r = Routine.query.get(int(request.form['routine_id']))
            if r and r.user_id == current_user.id:
                db.session.delete(r)
                db.session.commit()
        return redirect(url_for('module_c.routines_tracker'))

    routines = Routine.query.filter_by(user_id=current_user.id).all()
    total_r = len(routines)
    done_r = sum(1 for r in routines if r.is_completed)
    completion_pct = round((done_r / total_r) * 100) if total_r > 0 else 0

    # Upcoming Academic Deadlines for Calendar Overview
    upcoming_assignments = Assignment.query.order_by(Assignment.deadline.asc()).limit(6).all()
    subject_map = {s.id: s for s in Subject.query.all()}

    return render_template(
        'routines.html',
        active_page='routines',
        routines=routines,
        completion_pct=completion_pct,
        done_r=done_r,
        total_r=total_r,
        upcoming_assignments=upcoming_assignments,
        subject_map=subject_map
    )


@module_c.route('/collaborate', methods=['GET', 'POST'])
@login_required
def projects_forum():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_group':
            db.session.add(ProjectGroup(
                name=request.form['name'],
                subject_id=int(request.form['subject_id']),
                created_by=current_user.id,
                members_list=request.form.get('members_list', current_user.full_name)
            ))
            db.session.commit()
        elif action == 'add_group_task':
            db.session.add(GroupTask(
                group_id=int(request.form['group_id']),
                title=request.form['title'],
                assigned_to=request.form['assigned_to'],
                deadline=request.form['deadline']
            ))
            db.session.commit()
        elif action == 'toggle_group_task':
            gt = GroupTask.query.get(int(request.form['task_id']))
            if gt:
                gt.is_done = not gt.is_done
                db.session.commit()
        elif action == 'create_post':
            db.session.add(ForumPost(
                subject_id=int(request.form['subject_id']),
                author_id=current_user.id,
                title=request.form['title'],
                body=request.form['body']
            ))
            db.session.commit()
        elif action == 'add_reply':
            db.session.add(ForumReply(
                post_id=int(request.form['post_id']),
                author_id=current_user.id,
                body=request.form['body']
            ))
            db.session.commit()
        elif action == 'resolve_post':
            fp = ForumPost.query.get(int(request.form['post_id']))
            if fp:
                fp.is_resolved = not fp.is_resolved
                db.session.commit()
        return redirect(url_for('module_c.projects_forum'))

    subjects = Subject.query.all()
    subject_map = {s.id