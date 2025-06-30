import subprocess
import json

proc = subprocess.Popen(
    ["python", "app.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Request tool listing
proc.stdin.write(json.dumps({"type": "list_tools"}) + "\n")
proc.stdin.flush()

# Read response
print(proc.stdout.readline())
