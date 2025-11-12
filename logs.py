from datetime import datetime

def _write(level, msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def info(msg):
    _write("INFO", msg)

def warn(msg):
    _write("WARNING", msg)

def error(msg):
    _write("ERROR", msg)