#!/usr/bin/env python3
"""
Debug version - shows exactly what's happening
"""

import os
import sys
from dotenv import load_dotenv

print("="*70)
print("STEP 1: Loading environment")
print("="*70)

load_dotenv()
sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY", "")

if not sdk_key:
    print("❌ No SDK key found in .env")
    print("\nChecking .env file:")
    if os.path.exists('.env'):
        print("✅ .env file exists")
        with open('.env', 'r') as f:
            for line in f:
                if 'LAUNCHDARKLY' in line:
                    print(f"   Found: {line.strip()[:40]}...")
    else:
        print("❌ .env file not found!")
    sys.exit(1)

print(f"✅ SDK Key found: {sdk_key[:25]}...")

print("\n" + "="*70)
print("STEP 2: Importing modules")
print("="*70)

try:
    import database as db
    print("✅ database module imported")
except Exception as e:
    print(f"❌ Error importing database: {e}")
    sys.exit(1)

try:
    import ldclient
    from ldclient import Context
    from ldclient.config import Config
    print("✅ LaunchDarkly modules imported")
except ImportError as e:
    print(f"❌ Error importing LaunchDarkly: {e}")
    print("\nRun: pip3 install launchdarkly-server-sdk")
    sys.exit(1)

print("\n" + "="*70)
print("STEP 3: Initializing database")
print("="*70)

try:
    db.init_db()
    print("✅ Database initialized")
except Exception as e:
    print(f"❌ Error initializing database: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("STEP 4: Connecting to LaunchDarkly")
print("="*70)

try:
    config = Config(sdk_key=sdk_key)
    ldclient.set_config(config)
    ld_client = ldclient.get()
    print("✅ Client created")
    
    import time
    print("⏳ Waiting for initialization (5 seconds)...")
    time.sleep(5)
    
    if ld_client.is_initialized():
        print("✅ LaunchDarkly CONNECTED!")
    else:
        print("❌ LaunchDarkly NOT initialized")
        print("\nPossible issues:")
        print("  1. SDK key is invalid")
        print("  2. No internet connection")
        print("  3. Firewall blocking LaunchDarkly")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error connecting to LaunchDarkly: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("STEP 5: Loading users")
print("="*70)

usernames = ['alice', 'bob', 'carol', 'david', 'eve']
users = []

for username in usernames:
    user = db.get_user_by_username(username)
    if user:
        users.append(dict(user))
        print(f"✅ Found user: {username}")
    else:
        print(f"❌ User not found: {username}")

if not users:
    print("\n❌ No users found!")
    print("The app needs to be run first to create demo users.")
    sys.exit(1)

print(f"\n✅ Total users loaded: {len(users)}")

print("\n" + "="*70)
print("STEP 6: Testing flag evaluation")
print("="*70)

test_user = users[0]
context = (Context.builder(f"user-{test_user['id']}")
          .kind("user")
          .name(test_user['username'])
          .set("email", test_user['email'])
          .set("plan", test_user['plan'])
          .build())

print(f"Testing with user: {test_user['username']}")
print(f"Context key: {context.key}")

try:
    progress_value = ld_client.variation("progress-metrics", context, None)
    print(f"✅ Flag evaluated: progress-metrics = {progress_value}")
    
    if progress_value is None:
        print("\n⚠️  WARNING: Flag returned None")
        print("This means the flag doesn't exist in LaunchDarkly")
        print("Create 'progress-metrics' flag first!")
    
except Exception as e:
    print(f"❌ Error evaluating flag: {e}")

print("\n" + "="*70)
print("STEP 7: Testing event tracking")
print("="*70)

try:
    print("Sending test event...")
    ld_client.track("task-completed", context)
    print("✅ Event sent")
    
    print("Flushing events...")
    ld_client.flush()
    print("✅ Events flushed")
    
    print("\n✅ Event tracking works!")
    print("Check LaunchDarkly in 2-3 minutes to see if event appears")
    
except Exception as e:
    print(f"❌ Error tracking event: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("STEP 8: Creating sample data (just 1 user)")
print("="*70)

try:
    user = users[0]
    context = (Context.builder(f"user-{user['id']}")
              .kind("user")
              .name(user['username'])
              .set("email", user['email'])
              .set("plan", user['plan'])
              .build())
    
    print(f"Creating 3 tasks for {user['username']}...")
    
    for i in range(3):
        task_id = db.add_task(user['id'], f"Test task {i+1}", "General", "Medium")
        print(f"  ✅ Created task {task_id}")
        
        # Track creation
        ld_client.track("task-created", context)
    
    print("\nCompleting 2 tasks...")
    tasks = db.get_tasks(user['id'])
    
    for task in tasks[:2]:
        db.toggle_task(task['id'], user['id'])
        print(f"  ✅ Completed task {task['id']}")
        
        # Track completion
        ld_client.track("task-completed", context)
    
    print("\nFlushing events...")
    ld_client.flush()
    
    print("\n✅ Sample data created!")
    print(f"Sent 3 'task-created' events")
    print(f"Sent 2 'task-completed' events")
    
except Exception as e:
    print(f"❌ Error creating sample data: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)

print("""
If all steps passed:
  1. Wait 2-3 minutes
  2. Go to LaunchDarkly → Experiments
  3. Check if "Metric last seen" updated
  4. If yes, run the full generate_test_data.py script

If any step failed:
  - Check the error messages above
  - Most common issue: SDK key from wrong environment
""")

ld_client.close()