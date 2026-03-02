#!/usr/bin/env python3
"""
Task Manager with LaunchDarkly Feature Flags & Experiments
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
from functools import wraps
import time

import database as db

load_dotenv()

logging.getLogger('ldclient').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

db.init_db()

# LaunchDarkly Setup
import ldclient
from ldclient import Context
from ldclient.config import Config

sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY", "")

if sdk_key:
    # Simple config - use defaults which work fine
    ld_config = Config(sdk_key=sdk_key)
    ldclient.set_config(ld_config)
    ld_client = ldclient.get()
    
    # Wait for initialization
    if ld_client.is_initialized():
        print(f"\n✓ LaunchDarkly initialized successfully")
    else:
        print(f"\n✗ LaunchDarkly failed to initialize")
else:
    ld_client = None
    print("\nNo LaunchDarkly SDK key found. Running without feature flags.")


def get_flag(flag_key, context, default=False):
    """Evaluate a feature flag - this also sends an evaluation event"""
    if ld_client and ld_client.is_initialized():
        value = ld_client.variation(flag_key, context, default)
        print(f"[FLAG] {flag_key} = {value} for {context.key}")
        return value
    return default


def track_event(event_name, context, data=None, metric_value=None):
    """Track a custom event"""
    if ld_client and ld_client.is_initialized():
        if metric_value is not None:
            ld_client.track(event_name, context, data, metric_value)
        elif data is not None:
            ld_client.track(event_name, context, data)
        else:
            ld_client.track(event_name, context)
        
        # Flush immediately to ensure event is sent
        ld_client.flush()
        print(f"[EVENT] {event_name} tracked and flushed for {context.key}")
        return True
    return False


def get_ld_context(user=None):
    """Build a LaunchDarkly context from user data"""
    if user:
        return (Context.builder(f"user-{user['id']}")
                .kind("user")
                .name(user['username'])
                .set("email", user['email'])
                .set("plan", user['plan'])
                .set("registered", user['created_at'][:10])
                .build())
    else:
        return (Context.builder("anonymous")
                .kind("user")
                .anonymous(True)
                .build())


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' in session:
        return db.get_user_by_id(session['user_id'])
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = db.verify_password(username, password)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            context = get_ld_context(dict(user))
            track_event("user-login", context)
            
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    demo_users = ['alice', 'bob', 'carol', 'david', 'eve']
    return render_template('login.html', demo_users=demo_users)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    user = get_current_user()
    context = get_ld_context(dict(user))
    
    print(f"\n{'='*60}")
    print(f"INDEX PAGE - User: {user['username']}")
    print(f"{'='*60}")
    
    tasks = db.get_tasks(user['id'])
    
    # Evaluate all flags
    dark_mode = get_flag("dark-mode", context, False)
    
    show_stats = get_flag("task-stats", context, False)
    stats = None
    if show_stats:
        stats = {
            "total": len(tasks),
            "done": len([t for t in tasks if t["done"]]),
            "pending": len([t for t in tasks if not t["done"]])
        }
    
    search_enabled = get_flag("task-search", context, False)
    search_query = ""
    filtered_tasks = tasks
    
    if search_enabled:
        search_query = request.args.get("q", "").lower()
        if search_query:
            filtered_tasks = [t for t in tasks if search_query in t["title"].lower()]
    
    categories_enabled = get_flag("task-categories", context, False)
    priority_enabled = get_flag("task-priority", context, False)
    due_dates_enabled = get_flag("task-due-dates", context, False)
    
    # CRITICAL: Evaluate the experiment flag
    # This creates the exposure event that registers the user in the experiment
    progress_metrics_enabled = get_flag("progress-metrics", context, False)
    print(f">>> EXPERIMENT FLAG: progress-metrics = {progress_metrics_enabled}")
    
    progress_data = None
    if progress_metrics_enabled:
        progress_data = db.get_progress_data(user['id'])
        track_event("progress-chart-viewed", context)
        db.log_event(user['id'], 'progress-chart-viewed')
    
    flags = {
        "dark_mode": dark_mode,
        "stats": show_stats,
        "search": search_enabled,
        "categories": categories_enabled,
        "priority": priority_enabled,
        "due_dates": due_dates_enabled,
        "progress_metrics": progress_metrics_enabled
    }
    
    print(f"{'='*60}\n")
    
    return render_template(
        "index.html",
        user=user,
        tasks=filtered_tasks,
        flags=flags,
        stats=stats,
        progress_data=progress_data,
        search_query=search_query
    )


@app.route('/add', methods=['POST'])
@login_required
def add():
    user = get_current_user()
    context = get_ld_context(dict(user))
    
    title = request.form.get('title', '').strip()
    if not title:
        return redirect(url_for('index'))
    
    category = 'General'
    priority = 'Medium'
    due_date = None
    
    if get_flag("task-categories", context, False):
        category = request.form.get('category', 'General')
    
    if get_flag("task-priority", context, False):
        priority = request.form.get('priority', 'Medium')
    
    if get_flag("task-due-dates", context, False):
        due_date = request.form.get('due', None)
    
    db.add_task(user['id'], title, category, priority, due_date)
    
    track_event("task-created", context)
    db.log_event(user['id'], 'task-created')
    
    return redirect(url_for('index'))


@app.route('/toggle/<int:task_id>')
@login_required
def toggle(task_id):
    user = get_current_user()
    context = get_ld_context(dict(user))
    
    print(f"\n{'='*60}")
    print(f"TOGGLE TASK EVENT")
    print(f"{'='*60}")
    print(f"User: {user['username']} (ID: {user['id']})")
    print(f"Context Key: {context.key}")
    print(f"Task ID: {task_id}")
    print(f"LD Client Initialized: {ld_client.is_initialized() if ld_client else False}")
    
    # CRITICAL: Re-evaluate the experiment flag before tracking
    # This ensures the user is in the experiment context
    progress_enabled = get_flag("progress-metrics", context, False)
    print(f">>> Experiment Flag: progress-metrics = {progress_enabled}")
    
    # Toggle the task
    new_status = db.toggle_task(task_id, user['id'])
    print(f"Task Status Changed: {new_status} ({'COMPLETED' if new_status == 1 else 'INCOMPLETE'})")
    
    # Only track completion events (not un-completion)
    if new_status == 1:
        print(f"\n>>> TRACKING task-completed EVENT <<<")
        
        # Track the event
        success = track_event("task-completed", context)
        
        if success:
            print(f"✓ LaunchDarkly event sent successfully")
        else:
            print(f"✗ LaunchDarkly event failed to send")
        
        # Also log to local database
        db.log_event(user['id'], 'task-completed')
        print(f"✓ Event logged to local database")
    else:
        print(f"Task marked incomplete - no event tracked")
    
    print(f"{'='*60}\n")
    
    return redirect(url_for('index'))


@app.route('/delete/<int:task_id>')
@login_required
def delete(task_id):
    user = get_current_user()
    db.delete_task(task_id, user['id'])
    return redirect(url_for('index'))


@app.route('/api/flags')
def api_flags():
    user = get_current_user()
    context = get_ld_context(dict(user) if user else None)
    
    flags = {}
    flag_keys = ["dark-mode", "task-stats", "task-search", 
                 "task-categories", "task-priority", "task-due-dates", "progress-metrics"]
    
    for key in flag_keys:
        flags[key] = get_flag(key, context, False)
    
    return jsonify({
        "launchdarkly_initialized": ld_client.is_initialized() if ld_client else False,
        "user": user['username'] if user else "anonymous",
        "context_key": context.key,
        "flags": flags
    })


@app.route('/api/progress')
@login_required
def api_progress():
    user = get_current_user()
    return jsonify(db.get_progress_data(user['id']))


@app.route('/api/test-event')
@login_required
def test_event():
    """Test endpoint to verify event tracking is working"""
    user = get_current_user()
    context = get_ld_context(dict(user))
    
    # Evaluate the flag first
    progress_enabled = get_flag("progress-metrics", context, False)
    
    # Send a test event
    success = track_event("task-completed", context)
    
    return jsonify({
        "user": user['username'],
        "context_key": context.key,
        "flag_value": progress_enabled,
        "event_sent": success,
        "timestamp": datetime.now().isoformat()
    })


@app.teardown_appcontext
def cleanup(error):
    """Ensure events are flushed when app context ends"""
    if ld_client and ld_client.is_initialized():
        ld_client.flush()


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" TASK MANAGER - LaunchDarkly Server-Side Experiment")
    print("="*70)
    
    if ld_client:
        if ld_client.is_initialized():
            print(f"\n✓ LaunchDarkly SDK: Connected and Ready")
        else:
            print(f"\n✗ LaunchDarkly SDK: Failed to Initialize")
            print(f"  Check your LAUNCHDARKLY_SDK_KEY in .env")
    else:
        print("\n✗ LaunchDarkly SDK: Not Configured")
        print(f"  Add LAUNCHDARKLY_SDK_KEY to .env file")
    
    print("\n" + "-"*70)
    print("EXPERIMENT SETUP:")
    print("-"*70)
    print("Flag Name:      progress-metrics")
    print("Metric Name:    Task Completed (display name)")
    print("Event Key:      task-completed")
    print("Hypothesis:     Users with progress metrics complete more tasks")
    print("-"*70)
    
    print("\nDemo Users (password: 'demo' for all):")
    print("  • alice (premium)  • bob (free)     • carol (free)")
    print("  • david (premium)  • eve (free)")
    
    print("\n" + "="*70)
    print("Server Starting: http://localhost:5000")
    print("="*70 + "\n")
    
    try:
        app.run(debug=True, port=5000, use_reloader=False, host='0.0.0.0')
    finally:
        # Flush any remaining events on shutdown
        if ld_client and ld_client.is_initialized():
            print("\nFlushing remaining events...")
            ld_client.flush()
            time.sleep(1)
            ld_client.close()