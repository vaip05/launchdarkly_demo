"""
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
