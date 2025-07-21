#!/usr/bin/env python3
"""
WSGI application for the Interactive County Map
Can be used with Gunicorn for production deployment
"""

import os
import sys
from pathlib import Path
import mimetypes
from urllib.parse import unquote
import json

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


class WSGIApp:
    def __init__(self, static_dir=None):
        self.static_dir = Path(static_dir or Path(__file__).parent)
        # Ensure proper MIME types
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("image/png", ".png")
        mimetypes.add_type("image/jpeg", ".jpg")
        mimetypes.add_type("image/jpeg", ".jpeg")
        mimetypes.add_type("application/json", ".json")
        mimetypes.add_type("text/plain", ".txt")

    def __call__(self, environ, start_response):
        """WSGI application callable"""
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]

        # Handle CORS preflight requests
        if method == "OPTIONS":
            return self.handle_cors_preflight(start_response)

        # Handle static file requests
        if method == "GET":
            return self.serve_static_file(path, start_response)

        # Method not allowed
        start_response(
            "405 Method Not Allowed",
            [
                ("Content-Type", "text/plain"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )
        return [b"Method Not Allowed"]

    def handle_cors_preflight(self, start_response):
        """Handle CORS preflight OPTIONS requests"""
        headers = [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type"),
            ("Access-Control-Max-Age", "86400"),  # 24 hours
        ]
        start_response("200 OK", headers)
        return [b""]

    def serve_static_file(self, path, start_response):
        """Serve static files with proper headers"""
        try:
            # Clean up the path
            if path == "/":
                path = "/index.html"

            # Remove leading slash and decode URL
            file_path = unquote(path.lstrip("/"))
            full_path = self.static_dir / file_path

            # Security check - ensure file is within static directory
            try:
                full_path.resolve().relative_to(self.static_dir.resolve())
            except ValueError:
                start_response("403 Forbidden", [("Content-Type", "text/plain")])
                return [b"Forbidden"]

            # Check if file exists
            if not full_path.exists() or not full_path.is_file():
                start_response("404 Not Found", [("Content-Type", "text/plain")])
                return [b"File Not Found"]

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(full_path))
            if mime_type is None:
                mime_type = "application/octet-stream"

            # Read file content
            with open(full_path, "rb") as f:
                content = f.read()

            # Prepare headers
            headers = [
                ("Content-Type", mime_type),
                ("Content-Length", str(len(content))),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type"),
                # Development headers - disable caching
                ("Cache-Control", "no-cache, no-store, must-revalidate"),
                ("Pragma", "no-cache"),
                ("Expires", "0"),
            ]

            start_response("200 OK", headers)
            return [content]

        except Exception as e:
            # Log error in production you'd want proper logging
            print(f"Error serving {path}: {e}")
            start_response(
                "500 Internal Server Error", [("Content-Type", "text/plain")]
            )
            return [b"Internal Server Error"]


# Create the WSGI application instance
application = WSGIApp()

if __name__ == "__main__":
    # For development, fall back to the simple server
    print("⚠️  For development, use: python server.py")
    print("🚀 For production, use: gunicorn wsgi:application")
    sys.exit(1)
