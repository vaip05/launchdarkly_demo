import os
from dotenv import load_dotenv
import time

load_dotenv()

import ldclient
from ldclient import Context
from ldclient.config import Config

sdk_key = os.getenv("LAUNCHDARKLY_SDK_KEY", "")

print(f"SDK Key: {sdk_key[:20]}...")

# Initialize
config = Config(sdk_key=sdk_key)
ldclient.set_config(config)
client = ldclient.get()

print(f"Initialized: {client.is_initialized()}")

if client.is_initialized():
    # Create context
    context = Context.builder("test-user-999").kind("user").name("Test User").build()
    
    # Evaluate flag
    flag_value = client.variation("progress-metrics", context, False)
    print(f"Flag value: {flag_value}")
    
    # Send event
    print("Sending event...")
    client.track("task-completed", context)
    
    # Flush
    print("Flushing...")
    client.flush()
    
    # Wait
    print("Waiting 5 seconds...")
    time.sleep(5)
    
    # Flush again
    client.flush()
    
    print("Done! Check LaunchDarkly in 2-3 minutes.")
    
    # Close
    client.close()
else:
    print("ERROR: SDK did not initialize!")
    print("Check your SDK key.")