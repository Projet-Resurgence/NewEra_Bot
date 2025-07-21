#!/usr/bin/python3

import http.server
import socketserver
import os
import sys
import threading
import gzip
import mimetypes
from pathlib import Path
from urllib.parse import unquote

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Handle requests in a separate thread for better performance."""

    daemon_threads = True
    allow_reuse_address = True


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Enhanced HTTP request handler with better performance and features"""

    def __init__(self, *args, **kwargs):
        # Ensure proper MIME types
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("image/jpeg", ".jpg")
        mimetypes.add_type("image/jpeg", ".jpeg")
        mimetypes.add_type("application/json", ".json")
        super().__init__(*args, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200, "OK")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")  # 24 hours
        self.end_headers()

    def end_headers(self):
        # Add CORS headers to allow local file access
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Disable caching for development
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def guess_type(self, path):
        """Ensure correct MIME types for our files"""
        mimetype, encoding = mimetypes.guess_type(path)
        if path.endswith(".js"):
            return "application/javascript"
        elif path.endswith(".css"):
            return "text/css"
        elif path.endswith(".png"):
            return "image/png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"):
            return "image/jpeg"
        elif path.endswith(".json"):
            return "application/json"
        return mimetype or "application/octet-stream"

    def do_GET(self):
        """Enhanced GET handler with better error handling"""
        try:
            # Security check for path traversal
            path = unquote(self.path)
            if ".." in path or path.startswith("//"):
                self.send_error(403, "Forbidden")
                return

            super().do_GET()
        except Exception as e:
            print(f"Error handling GET request for {self.path}: {e}")
            self.send_error(500, "Internal Server Error")

    def log_message(self, format, *args):
        """Enhanced logging with timestamps and better formatting"""
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")

    def version_string(self):
        """Return server version string"""
        return f"InteractiveCountyMapServer/1.0"


def main():
    # Change to the script directory
    os.chdir(SCRIPT_DIR)

    PORT = 8000

    # Check if Gunicorn is available and suggest it for production
    try:
        import gunicorn

        print(f"✨ Gunicorn detected! For production use:")
        print(f"   gunicorn -c gunicorn.conf.py wsgi:application")
        print(f"   or: gunicorn --bind 0.0.0.0:8000 --workers 4 wsgi:application")
        print()
    except ImportError:
        print(f"💡 Install Gunicorn for production: pip install gunicorn")
        print()

    try:
        with ThreadedHTTPServer(("", PORT), HTTPRequestHandler) as httpd:
            print(f"🗺️  Interactive County Map Server (Development)")
            print(f"📍 Serving at: http://localhost:{PORT}")
            print(f"📂 Directory: {SCRIPT_DIR}")
            print(f"🌐 Open http://localhost:{PORT} in your browser")
            print(f"🧵 Multi-threaded server ready")
            print(f"⏹️  Press Ctrl+C to stop the server")
            print("-" * 60)

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n👋 Server stopped!")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use!")
            print(f"💡 Try a different port or stop the existing server")
            # Try alternative ports
            for alt_port in [8001, 8080, 3000]:
                try:
                    with ThreadedHTTPServer(
                        ("", alt_port), HTTPRequestHandler
                    ) as httpd:
                        print(
                            f"🔄 Trying alternative port: http://localhost:{alt_port}"
                        )
                        httpd.serve_forever()
                        break
                except OSError:
                    continue
        else:
            print(f"❌ Error starting server: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
