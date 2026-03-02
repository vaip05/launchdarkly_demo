#!/usr/bin/env python3
"""
Generate both flag evaluations AND events
"""

import os
import sys
from dotenv import load_dotenv
import time
import random

load_dotenv()

import ldclient
from ldclient import Context
from ldclient.config import Config
import database as db

# Initialize
sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY", "")
config = Config(sdk_key=sdk_key)
ldclient.set_config(config)
ld_client = ldclient.get()

time.sleep(3)

if not ld_client.is_initialized():
    print("❌ Not connected to LaunchDarkly")
    sys.exit(1)

print("✅ LaunchDarkly connected\n")

db.init_db()

usernames = ['alice', 'bob', 'carol', 'david', 'eve']
flags = ['dark-mode', 'task-stats', 'task-search', 'task-categories', 
         'task-priority', 'task-due-dates', 'progress-metrics']

task_ideas = ["Buy groceries", "Finish report", "Call dentist", "Send email",
              "Review code", "Update docs", "Schedule meeting", "Pay bills"]

print("="*60)
print("GENERATING COMPLETE DATA")
print("="*60)

total_evaluations = 0
total_events = 0

for username in usernames:
    user = db.get_user_by_username(username)
    if not user:
        continue
    
    user_dict = dict(user)
    context = (Context.builder(f"user-{user_dict['id']}")
              .kind("user")
              .name(user_dict['username'])
              .set("email", user_dict['email'])
              .set("plan", user_dict['plan'])
              .build())
    
    print(f"\n👤 {username} ({user_dict['plan']})")
    
    # Simulate 8-12 sessions
    num_sessions = random.randint(8, 12)
    
    for session in range(num_sessions):
        # 1. EVALUATE FLAGS (simulates page load)
        flag_values = {}
        for flag in flags:
            flag_values[flag] = ld_client.variation(flag, context, False)
            total_evaluations += 1
        
        # 2. TRACK LOGIN EVENT
        ld_client.track("user-login", context)
        total_events += 1
        
        # 3. TRACK PROGRESS CHART VIEW (if applicable)
        if flag_values.get('progress-metrics'):
            ld_client.track("progress-chart-viewed", context)
            total_events += 1
        
        # 4. CREATE TASKS
        num_tasks = random.randint(2, 4)
        for _ in range(num_tasks):
            task_title = random.choice(task_ideas)
            db.add_task(user_dict['id'], task_title)
            ld_client.track("task-created", context)
            total_events += 1
        
        # 5. COMPLETE TASKS
        tasks = db.get_tasks(user_dict['id'])
        incomplete = [t for t in tasks if not t['done']]
        
        # Higher completion rate if user sees progress
        completion_rate = 0.75 if flag_values.get('progress-metrics') else 0.60
        num_complete = int(len(incomplete) * completion_rate)
        
        for task in incomplete[:num_complete]:
            db.toggle_task(task['id'], user_dict['id'])
            ld_client.track("task-completed", context)
            total_events += 1
        
        time.sleep(0.05)  # Small delay
    
    ld_client.flush()
    print(f"   ✅ {num_sessions} sessions")
    print(f"   ✅ {num_sessions * len(flags)} flag evaluations")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"Total flag evaluations: {total_evaluations}")
print(f"Total custom events: {total_events}")
print("\nWait 2-3 minutes, then check LaunchDarkly")

ld_client.close()