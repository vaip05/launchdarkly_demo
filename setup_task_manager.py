#!/usr/bin/env python3
"""
Task Manager Installation Script
Use this script to set up the Task Manager demo with LaunchDarkly integration. It will create necessary files and install dependencies.
================================
Run: python3 setup_task_manager.py
"""

import os
import sys
import subprocess
import secrets

PROJECT_NAME = "task-manager-ld"

REQUIRED_PACKAGES = [
    "flask",
    "python-dotenv", 
    "launchdarkly-server-sdk",
    "pyngrok"
]


def get_database_py():
    return r'''"""
Lightweight SQLite database for demo purposes.
Pre-seeded with 5 test users.
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta
import random

DATABASE = 'taskmanager.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL,
            plan TEXT DEFAULT 'free',
            created_at TEXT NOT NULL
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            category TEXT DEFAULT 'General',
            priority TEXT DEFAULT 'Medium',
            due_date TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    seed_users(conn)
    conn.close()
    print("  Database initialized!")


def seed_users(conn):
    demo_users = [
        ('alice', 'demo', 'alice@example.com', 'premium'),
        ('bob', 'demo', 'bob@example.com', 'free'),
        ('carol', 'demo', 'carol@example.com', 'free'),
        ('david', 'demo', 'david@example.com', 'premium'),
        ('eve', 'demo', 'eve@example.com', 'free'),
    ]
    
    c = conn.cursor()
    
    for username, password, email, plan in demo_users:
        try:
            days_ago = random.randint(1, 30)
            created = (datetime.now() - timedelta(days=days_ago)).isoformat()
            c.execute("""
                INSERT INTO users (username, password_hash, email, plan, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username, hash_password(password), email, plan, created))
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()


def get_user_by_username(username):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def verify_password(username, password):
    user = get_user_by_username(username)
    if user and user['password_hash'] == hash_password(password):
        return user
    return None


def get_tasks(user_id):
    conn = get_db()
    tasks = conn.execute(
        'SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(t) for t in tasks]


def add_task(user_id, title, category='General', priority='Medium', due_date=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (user_id, title, category, priority, due_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, title, category, priority, due_date, datetime.now().isoformat()))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id


def toggle_task(task_id, user_id):
    conn = get_db()
    task = conn.execute(
        'SELECT done FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()
    
    if task:
        new_status = 0 if task['done'] else 1
        completed_at = datetime.now().isoformat() if new_status else None
        conn.execute(
            'UPDATE tasks SET done = ?, completed_at = ? WHERE id = ?',
            (new_status, completed_at, task_id)
        )
        conn.commit()
    conn.close()
    return new_status if task else None


def delete_task(task_id, user_id):
    conn = get_db()
    conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()


def get_progress_data(user_id):
    conn = get_db()
    
    completions = conn.execute("""
        SELECT DATE(completed_at) as date, COUNT(*) as count
        FROM tasks
        WHERE user_id = ? AND done = 1 AND completed_at IS NOT NULL
        AND completed_at >= DATE('now', '-7 days')
        GROUP BY DATE(completed_at)
        ORDER BY date
    """, (user_id,)).fetchall()
    
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) as completed
        FROM tasks WHERE user_id = ?
    """, (user_id,)).fetchone()
    
    conn.close()
    
    dates = []
    counts = []
    completion_dict = {row['date']: row['count'] for row in completions}
    
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        dates.append((datetime.now() - timedelta(days=i)).strftime('%a'))
        counts.append(completion_dict.get(date, 0))
    
    return {
        'labels': dates,
        'data': counts,
        'total_tasks': stats['total'] or 0,
        'completed_tasks': stats['completed'] or 0,
        'completion_rate': round((stats['completed'] or 0) / max(stats['total'] or 1, 1) * 100)
    }


def log_event(user_id, event_name):
    conn = get_db()
    conn.execute(
        'INSERT INTO events (user_id, event_name, timestamp) VALUES (?, ?, ?)',
        (user_id, event_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
'''


def get_app_py():
    return r'''"""
Task Manager with LaunchDarkly Feature Flags & Experiments
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import os
from dotenv import load_dotenv
from datetime import datetime
import logging
from functools import wraps

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
    ld_config = Config(sdk_key=sdk_key)
    ldclient.set_config(ld_config)
    ld_client = ldclient.get()
    print(f"\nLaunchDarkly initialized: {ld_client.is_initialized()}")
else:
    ld_client = None
    print("\nNo LaunchDarkly SDK key found. Running without feature flags.")


def get_flag(flag_key, context, default=False):
    if ld_client and ld_client.is_initialized():
        return ld_client.variation(flag_key, context, default)
    return default


def track_event(event_name, context):
    if ld_client and ld_client.is_initialized():
        ld_client.track(event_name, context)


def get_ld_context(user=None):
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
    
    tasks = db.get_tasks(user['id'])
    
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
    
    progress_metrics_enabled = get_flag("progress-metrics", context, False)
    
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
    
    new_status = db.toggle_task(task_id, user['id'])
    
    if new_status == 1:
        track_event("task-completed", context)
        db.log_event(user['id'], 'task-completed')
    
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


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TASK MANAGER - LaunchDarkly Experiment Demo")
    print("="*60)
    
    if ld_client:
        status = "Connected" if ld_client.is_initialized() else "Not Connected"
        print(f"\nLaunchDarkly: {status}")
    else:
        print("\nLaunchDarkly: No SDK key configured")
    
    print("\nDemo Users (password: 'demo' for all):")
    print("  alice (premium), bob (free), carol (free)")
    print("  david (premium), eve (free)")
    
    print("\nExperiment: progress-metrics")
    print("Hypothesis: Users who see progress metrics complete more tasks")
    
    print("\n" + "="*60)
    print("Open: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, use_reloader=False, host='0.0.0.0')
'''


def get_run_py():
    return r'''#!/usr/bin/env python3
"""
Run script with optional ngrok tunnel.
Usage: python run.py [--ngrok]
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def run_with_ngrok():
    from pyngrok import ngrok, conf
    
    ngrok_token = os.getenv("NGROK_AUTHTOKEN", "")
    if ngrok_token:
        conf.get_default().auth_token = ngrok_token
    
    print("Starting ngrok tunnel...")
    tunnel = ngrok.connect(5000)
    print(f"\nPublic URL: {tunnel.public_url}")
    print("Share this URL to access your app from anywhere!\n")
    
    os.system("python app.py")


def run_local():
    os.system("python app.py")


if __name__ == "__main__":
    if "--ngrok" in sys.argv or "-n" in sys.argv:
        run_with_ngrok()
    else:
        run_local()
'''


def get_base_html():
    return '''<!DOCTYPE html>
<html lang="en" data-theme="{{ 'dark' if flags.dark_mode else 'light' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Manager</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-card: #ffffff;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --border-color: #dee2e6;
            --accent: #0d6efd;
            --accent-hover: #0b5ed7;
            --success: #198754;
            --danger: #dc3545;
            --warning: #ffc107;
        }
        
        [data-theme="dark"] {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --text-primary: #e8e8e8;
            --text-secondary: #a0a0a0;
            --border-color: #2a2a4a;
            --accent: #4dabf7;
            --accent-hover: #339af0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            transition: background 0.3s, color 0.3s;
        }
        
        .navbar {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .navbar h1 { font-size: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }
        .navbar-user { display: flex; align-items: center; gap: 1rem; }
        
        .user-badge {
            background: var(--accent);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }
        
        .btn-primary { background: var(--accent); color: white; }
        .btn-primary:hover { background: var(--accent-hover); }
        .btn-outline { background: transparent; border: 1px solid var(--border-color); color: var(--text-primary); }
        .btn-outline:hover { background: var(--bg-secondary); }
        .btn-danger { background: var(--danger); color: white; }
        
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        .card-title { font-size: 1.125rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
        
        .flash { padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }
        .flash-success { background: #d1e7dd; color: #0f5132; }
        .flash-error { background: #f8d7da; color: #842029; }
        .flash-warning { background: #fff3cd; color: #664d03; }
        .flash-info { background: #cff4fc; color: #055160; }
        
        .flag-indicator {
            position: fixed;
            bottom: 1rem;
            right: 1rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.5rem;
            font-size: 0.75rem;
            opacity: 0.7;
        }
        
        .flag-indicator:hover { opacity: 1; }
        
        .flag-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 4px;
        }
        
        .flag-dot.on { background: var(--success); }
        .flag-dot.off { background: var(--text-secondary); }
    </style>
</head>
<body>
    <nav class="navbar">
        <h1>Task Manager</h1>
        {% if user %}
        <div class="navbar-user">
            <span class="user-badge">{{ user.username }} ({{ user.plan }})</span>
            <a href="{{ url_for('logout') }}" class="btn btn-outline">Logout</a>
        </div>
        {% endif %}
    </nav>
    
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>
    
    {% if flags %}
    <div class="flag-indicator" title="Feature Flags">
        Flags: 
        <span class="flag-dot {{ 'on' if flags.dark_mode else 'off' }}"></span>DM
        <span class="flag-dot {{ 'on' if flags.progress_metrics else 'off' }}"></span>PM
        <span class="flag-dot {{ 'on' if flags.search else 'off' }}"></span>S
    </div>
    {% endif %}
    
    {% block scripts %}{% endblock %}
</body>
</html>
'''


def get_login_html():
    return '''{% extends "base.html" %}

{% block content %}
<div style="max-width: 400px; margin: 4rem auto;">
    <div class="card">
        <h2 class="card-title">Sign In</h2>
        
        <form method="POST" action="{{ url_for('login') }}">
            <div style="margin-bottom: 1rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Username</label>
                <input type="text" name="username" required autofocus
                    style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);"
                    placeholder="Enter username">
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Password</label>
                <input type="password" name="password" required
                    style="width: 100%; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);"
                    placeholder="Enter password">
            </div>
            
            <button type="submit" class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.75rem;">
                Sign In
            </button>
        </form>
    </div>
    
    <div class="card">
        <h3 class="card-title">Demo Users</h3>
        <p style="color: var(--text-secondary); margin-bottom: 1rem; font-size: 0.875rem;">
            Click to auto-fill (password: demo)
        </p>
        
        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
            {% for username in demo_users %}
            <button type="button" class="btn btn-outline demo-user-btn" data-username="{{ username }}"
                style="flex: 1; min-width: 80px; justify-content: center;">
                {{ username }}
            </button>
            {% endfor %}
        </div>
    </div>
    
    <div class="card" style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-card));">
        <h3 class="card-title">Experiment Info</h3>
        <p style="font-size: 0.875rem; color: var(--text-secondary); line-height: 1.6;">
            This demo runs an A/B experiment using LaunchDarkly. Some users will see 
            a Progress Metrics Chart while others will not. We measure if seeing 
            progress affects task completion rates.
        </p>
    </div>
</div>

<script>
    document.querySelectorAll('.demo-user-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelector('input[name="username"]').value = btn.dataset.username;
            document.querySelector('input[name="password"]').value = 'demo';
        });
    });
</script>
{% endblock %}
'''


def get_index_html():
    return '''{% extends "base.html" %}

{% block content %}

{% if flags.progress_metrics and progress_data %}
<div class="card" style="background: linear-gradient(135deg, var(--bg-secondary), var(--bg-card));">
    <h2 class="card-title">Your Progress</h2>
    
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="text-align: center; padding: 1rem; background: var(--bg-primary); border-radius: 8px;">
            <div style="font-size: 2rem; font-weight: bold; color: var(--accent);">{{ progress_data.total_tasks }}</div>
            <div style="font-size: 0.875rem; color: var(--text-secondary);">Total Tasks</div>
        </div>
        <div style="text-align: center; padding: 1rem; background: var(--bg-primary); border-radius: 8px;">
            <div style="font-size: 2rem; font-weight: bold; color: var(--success);">{{ progress_data.completed_tasks }}</div>
            <div style="font-size: 0.875rem; color: var(--text-secondary);">Completed</div>
        </div>
        <div style="text-align: center; padding: 1rem; background: var(--bg-primary); border-radius: 8px;">
            <div style="font-size: 2rem; font-weight: bold; color: var(--warning);">{{ progress_data.completion_rate }}%</div>
            <div style="font-size: 0.875rem; color: var(--text-secondary);">Completion Rate</div>
        </div>
    </div>
    
    <div style="height: 200px;"><canvas id="progressChart"></canvas></div>
</div>
{% endif %}

{% if flags.stats and stats %}
<div class="card">
    <div style="display: flex; justify-content: space-around; text-align: center;">
        <div>
            <div style="font-size: 1.5rem; font-weight: bold;">{{ stats.total }}</div>
            <div style="color: var(--text-secondary); font-size: 0.875rem;">Total</div>
        </div>
        <div>
            <div style="font-size: 1.5rem; font-weight: bold; color: var(--success);">{{ stats.done }}</div>
            <div style="color: var(--text-secondary); font-size: 0.875rem;">Done</div>
        </div>
        <div>
            <div style="font-size: 1.5rem; font-weight: bold; color: var(--warning);">{{ stats.pending }}</div>
            <div style="color: var(--text-secondary); font-size: 0.875rem;">Pending</div>
        </div>
    </div>
</div>
{% endif %}

{% if flags.search %}
<div class="card">
    <form method="GET" action="{{ url_for('index') }}" style="display: flex; gap: 0.5rem;">
        <input type="text" name="q" value="{{ search_query }}" placeholder="Search tasks..." 
            style="flex: 1; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);">
        <button type="submit" class="btn btn-primary">Search</button>
        {% if search_query %}<a href="{{ url_for('index') }}" class="btn btn-outline">Clear</a>{% endif %}
    </form>
</div>
{% endif %}

<div class="card">
    <h2 class="card-title">Add Task</h2>
    <form method="POST" action="{{ url_for('add') }}">
        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem;">
            <input type="text" name="title" required placeholder="What needs to be done?"
                style="flex: 2; min-width: 200px; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);">
            
            {% if flags.categories %}
            <select name="category" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);">
                <option value="General">General</option>
                <option value="Work">Work</option>
                <option value="Personal">Personal</option>
                <option value="Shopping">Shopping</option>
                <option value="Health">Health</option>
            </select>
            {% endif %}
            
            {% if flags.priority %}
            <select name="priority" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);">
                <option value="Low">Low</option>
                <option value="Medium" selected>Medium</option>
                <option value="High">High</option>
            </select>
            {% endif %}
            
            {% if flags.due_dates %}
            <input type="date" name="due" style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);">
            {% endif %}
            
            <button type="submit" class="btn btn-primary">Add Task</button>
        </div>
    </form>
</div>

<div class="card">
    <h2 class="card-title">Tasks ({{ tasks|length }})</h2>
    
    {% if tasks %}
    <ul style="list-style: none;">
        {% for task in tasks %}
        <li style="display: flex; align-items: center; gap: 1rem; padding: 1rem; border-bottom: 1px solid var(--border-color); {% if task.done %}opacity: 0.6;{% endif %}">
            <a href="{{ url_for('toggle', task_id=task.id) }}" style="font-size: 1.5rem; text-decoration: none;">
                {% if task.done %}[x]{% else %}[ ]{% endif %}
            </a>
            
            <div style="flex: 1;">
                <div style="{% if task.done %}text-decoration: line-through;{% endif %}">{{ task.title }}</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">
                    {% if flags.categories and task.category %}<span>{{ task.category }}</span>{% endif %}
                    {% if flags.priority and task.priority %}
                        <span style="margin-left: 0.5rem;">{{ task.priority }}</span>
                    {% endif %}
                    {% if flags.due_dates and task.due_date %}<span style="margin-left: 0.5rem;">{{ task.due_date }}</span>{% endif %}
                </div>
            </div>
            
            <a href="{{ url_for('delete', task_id=task.id) }}" class="btn btn-danger" style="padding: 0.25rem 0.5rem;">Delete</a>
        </li>
        {% endfor %}
    </ul>
    {% else %}
    <p style="text-align: center; color: var(--text-secondary); padding: 2rem;">No tasks yet. Add one above!</p>
    {% endif %}
</div>

{% endblock %}

{% block scripts %}
{% if flags.progress_metrics and progress_data %}
<script>
    const ctx = document.getElementById('progressChart').getContext('2d');
    const isDark = document.documentElement.dataset.theme === 'dark';
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: {{ progress_data.labels | tojson }},
            datasets: [{
                label: 'Tasks Completed',
                data: {{ progress_data.data | tojson }},
                backgroundColor: isDark ? 'rgba(77, 171, 247, 0.7)' : 'rgba(13, 110, 253, 0.7)',
                borderColor: isDark ? 'rgba(77, 171, 247, 1)' : 'rgba(13, 110, 253, 1)',
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, color: isDark ? '#a0a0a0' : '#6c757d' },
                    grid: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }
                },
                x: {
                    ticks: { color: isDark ? '#a0a0a0' : '#6c757d' },
                    grid: { display: false }
                }
            }
        }
    });
</script>
{% endif %}
{% endblock %}
'''


def get_requirements_txt():
    return '''flask>=2.0.0
python-dotenv>=1.0.0
launchdarkly-server-sdk>=9.0.0
pyngrok>=7.0.0
'''


def get_readme_md():
    return '''# Task Manager - LaunchDarkly Experiment Demo

A Flask-based task manager demonstrating LaunchDarkly feature flags and A/B experiments.

## Experiment

Hypothesis: Users who see progress metrics will complete more tasks.

Treatment: Progress metrics chart (enabled/disabled via progress-metrics flag)

Metrics:
- task-completed - Primary conversion metric
- progress-chart-viewed - Feature exposure
- task-created - User engagement

## Quick Start

Run locally:
    python run.py

Run with ngrok tunnel:
    python run.py --ngrok

## Demo Users

| Username | Password | Plan    |
|----------|----------|---------|
| alice    | demo     | premium |
| bob      | demo     | free    |
| carol    | demo     | free    |
| david    | demo     | premium |
| eve      | demo     | free    |

## Feature Flags

Create these flags in LaunchDarkly:

| Flag Key         | Type    | Description    |
|------------------|---------|----------------|
| dark-mode        | Boolean | Dark theme     |
| task-stats       | Boolean | Stats bar      |
| task-search      | Boolean | Search feature |
| task-categories  | Boolean | Categories     |
| task-priority    | Boolean | Priority       |
| task-due-dates   | Boolean | Due dates      |
| progress-metrics | Boolean | EXPERIMENT     |

## API Endpoints

- GET /api/flags - Current flag states
- GET /api/progress - User progress data
'''


def print_banner():
    print("""
============================================================
   Task Manager - LaunchDarkly Experiment Demo
   Installation Script
============================================================
    """)

# get user input for configuration
def get_user_input():
    print("\nAPI Key Configuration")
    print("-" * 40)
    
    print("\nLaunchDarkly SDK Key")
    print("Find it at: https://app.launchdarkly.com/settings/projects")
    print("Select your project -> Environments -> SDK Key")
    ld_key = input("\nEnter LaunchDarkly SDK Key (or press Enter to skip): ").strip()
    
    print("\nngrok Authtoken (optional, for public URL)")
    print("Get it at: https://dashboard.ngrok.com/get-started/your-authtoken")
    ngrok_token = input("\nEnter ngrok Authtoken (or press Enter to skip): ").strip()
    
    return ld_key, ngrok_token

# create directories
def create_directory_structure(base_path):
    print("\nCreating directory structure...")
    
    directories = [
        base_path,
        os.path.join(base_path, "templates")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  Created: {directory}")

# helper function to write files
def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Created: {path}")

# create all necessary files with content
def create_files(base_path, ld_key, ngrok_token):
    print("\nCreating project files...")
    
    # Python files
    write_file(os.path.join(base_path, "database.py"), get_database_py())
    write_file(os.path.join(base_path, "app.py"), get_app_py())
    write_file(os.path.join(base_path, "run.py"), get_run_py())
    
    # Templates
    write_file(os.path.join(base_path, "templates", "base.html"), get_base_html())
    write_file(os.path.join(base_path, "templates", "login.html"), get_login_html())
    write_file(os.path.join(base_path, "templates", "index.html"), get_index_html())
    
    # Config files
    write_file(os.path.join(base_path, "requirements.txt"), get_requirements_txt())
    write_file(os.path.join(base_path, "README.md"), get_readme_md())
    
    # .env file
    secret_key = secrets.token_hex(32)
    env_content = f"""# Task Manager Configuration

# Flask
SECRET_KEY={secret_key}

# LaunchDarkly
LAUNCHDARKLY_SDK_KEY={ld_key}

# ngrok (optional)
NGROK_AUTHTOKEN={ngrok_token}
"""
    write_file(os.path.join(base_path, ".env"), env_content)
    
    # .gitignore
    gitignore_content = """__pycache__/
*.py[cod]
*.so
.Python
venv/
ENV/
*.db
.env
.env.local
.idea/
.vscode/
*.swp
.DS_Store
Thumbs.db
"""
    write_file(os.path.join(base_path, ".gitignore"), gitignore_content)

# install dependencies using pip
def install_dependencies(base_path):
    print("\nInstalling dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r",
            os.path.join(base_path, "requirements.txt"),
            "-q"
        ])
        print("  Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error installing dependencies: {e}")
        return False


def print_success(base_path, ld_key, ngrok_token):
    print("""
============================================================
              INSTALLATION COMPLETE!
============================================================
    """)
    
    print(f"Project created at: {os.path.abspath(base_path)}")
    
    print("\n" + "-" * 60)
    print("NEXT STEPS")
    print("-" * 60)
    
    print(f"""
1. Navigate to project:
   cd {base_path}

2. Run the application:
   python run.py           # Local only
   python run.py --ngrok   # With public URL
    """)
    
    if not ld_key:
        print("""
NOTE: LaunchDarkly SDK key not provided!
Add it to .env file:
LAUNCHDARKLY_SDK_KEY=your-sdk-key-here
    """)
    
    print("""
3. Create these flags in LaunchDarkly:
   
   Flag Key          Type      Description
   ------------------------------------------------
   dark-mode         Boolean   Dark theme
   task-stats        Boolean   Stats bar
   task-search       Boolean   Search feature
   task-categories   Boolean   Task categories
   task-priority     Boolean   Priority levels
   task-due-dates    Boolean   Due dates
   progress-metrics  Boolean   EXPERIMENT

4. Set up the experiment (progress-metrics flag):
   - Create flag as Boolean
   - Set rollout: 50% true / 50% false
   - Create metric: "task-completed" (conversion)
   - Attach metric to flag
   - Start experiment!

5. Demo Users (password: 'demo'):
   alice (premium), bob (free), carol (free)
   david (premium), eve (free)
    """)
    
    print("-" * 60)
    print("Access your app at: http://localhost:5000")
    if ngrok_token:
        print("Or run with --ngrok for a public URL")
    print("-" * 60)

# main function for setup initiation
def main():
    print_banner()
    
    ld_key, ngrok_token = get_user_input()
    
    base_path = PROJECT_NAME
    
    print(f"\nInstalling to: {os.path.abspath(base_path)}")
    confirm = input("Continue? [Y/n]: ").strip().lower()
    
    if confirm == 'n':
        print("\nInstallation cancelled.")
        sys.exit(0)
    
    create_directory_structure(base_path)
    create_files(base_path, ld_key, ngrok_token)
    
    install_deps = input("\nInstall Python dependencies now? [Y/n]: ").strip().lower()
    if install_deps != 'n':
        install_dependencies(base_path)
    
    print_success(base_path, ld_key, ngrok_token)


if __name__ == "__main__":
    main()