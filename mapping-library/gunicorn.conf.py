# Gunicorn configuration file
# Usage: gunicorn -c gunicorn.conf.py wsgi:application

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "interactive-county-map"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure for HTTPS)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Performance tuning
preload_app = True
enable_stdio_inheritance = True


# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🗺️  Interactive County Map Server starting...")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 Reloading workers...")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"🚀 Server ready at http://{bind}")
    server.log.info(f"👥 Running with {workers} workers")


def on_exit(server):
    """Called just before exiting."""
    server.log.info("👋 Server shutting down...")
