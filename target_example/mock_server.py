# target_example/mock_server.py
"""
Mock Digital Learning Platform Sign-Up Portal
Runs a local HTTP server with CSRF token generation on every GET,
session tracking, and validation for School, Student ID, and matching Email.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import secrets
import time

VALID_RECORDS = {
    ("Apex High School", "STU-2024-001"): "alice.johnson@student.apex.edu",
    ("Apex High School", "STU-2024-005"): "eva.martinez@student.apex.edu",
    ("Stanford Online Learning", "STU-2024-008"): "henry.anderson@student.apex.edu",
}

# In-memory session store: session_id -> {csrf_token, created_at}
SESSIONS = {}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Learning Portal - Student Sign-Up</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f172a; color: #f8fafc; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; width: 100%; max-width: 480px; padding: 32px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { font-size: 24px; margin-bottom: 8px; color: #38bdf8; text-align: center; }
        p.subtitle { font-size: 14px; color: #94a3b8; text-align: center; margin-bottom: 24px; }
        .alert { padding: 12px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; }
        .alert-success { background: #064e3b; border: 1px solid #059669; color: #6ee7b7; }
        .alert-error { background: #450a0a; border: 1px solid #dc2626; color: #fca5a5; }
        .form-group { margin-bottom: 18px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #cbd5e1; }
        input, select { width: 100%; padding: 10px 14px; background: #0f172a; border: 1px solid #475569; border-radius: 6px; color: #f8fafc; font-size: 14px; }
        input:focus, select:focus { outline: none; border-color: #38bdf8; }
        button { width: 100%; padding: 12px; background: #0284c7; border: none; border-radius: 6px; color: #ffffff; font-weight: 600; font-size: 15px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        .footer { margin-top: 20px; font-size: 12px; color: #64748b; text-align: center; }
        .csrf-badge { display: block; font-family: monospace; font-size: 11px; color: #64748b; margin-top: 6px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Digital Learning Portal</h1>
        <p class="subtitle">Student Sign-Up & Verification</p>
        
        {ALERT_BLOCK}

        <form action="/signup" method="POST">
            <input type="hidden" name="_csrf_token" value="{CSRF_TOKEN}">

            <div class="form-group">
                <label for="school">School / Institution</label>
                <select id="school" name="school">
                    <option value="Apex High School">Apex High School</option>
                    <option value="Springfield Academy">Springfield Academy</option>
                    <option value="Lincoln Institute of Technology">Lincoln Institute of Technology</option>
                    <option value="Stanford Online Learning">Stanford Online Learning</option>
                    <option value="Global Digital Academy">Global Digital Academy</option>
                </select>
            </div>

            <div class="form-group">
                <label for="student_id">Student ID / Learner ID</label>
                <input type="text" id="student_id" name="student_id" placeholder="e.g. STU-2024-001" required>
            </div>

            <div class="form-group">
                <label for="email">Student Institutional Email</label>
                <input type="email" id="email" name="email" placeholder="e.g. alice.johnson@student.apex.edu" required>
            </div>

            <button type="submit">Verify & Sign Up</button>
            <span class="csrf-badge">Session Token: {CSRF_TOKEN}</span>
        </form>
        <div class="footer">Refreshes session & CSRF token on every request</div>
    </div>
</body>
</html>
"""

class PortalHandler(BaseHTTPRequestHandler):
    def get_session(self):
        cookie = self.headers.get("Cookie", "")
        session_id = None
        for item in cookie.split(";"):
            item = item.strip()
            if item.startswith("session_id="):
                session_id = item.split("=", 1)[1]
                break
        
        # Always issue a fresh CSRF token upon request to enforce trial refresh!
        if not session_id or session_id not in SESSIONS:
            session_id = secrets.token_hex(16)
        
        fresh_csrf = secrets.token_hex(24)
        SESSIONS[session_id] = {
            "csrf": fresh_csrf,
            "time": time.time()
        }
        return session_id, fresh_csrf

    def do_GET(self):
        session_id, csrf = self.get_session()
        html = HTML_TEMPLATE.replace("{ALERT_BLOCK}", "").replace("{CSRF_TOKEN}", csrf)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Set-Cookie", f"session_id={session_id}; Path=/; HttpOnly")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        cookie = self.headers.get("Cookie", "")
        session_id = None
        for item in cookie.split(";"):
            item = item.strip()
            if item.startswith("session_id="):
                session_id = item.split("=", 1)[1]
                break

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        params = urllib.parse.parse_qs(post_data)

        submitted_csrf = params.get("_csrf_token", [""])[0]
        school = params.get("school", [""])[0]
        student_id = params.get("student_id", [""])[0]
        email = params.get("email", [""])[0]

        # Check session & CSRF token
        valid_csrf = SESSIONS.get(session_id, {}).get("csrf", "")
        
        # New fresh CSRF for next trial
        new_session_id = secrets.token_hex(16)
        new_csrf = secrets.token_hex(24)
        SESSIONS[new_session_id] = {"csrf": new_csrf, "time": time.time()}

        if not submitted_csrf or submitted_csrf != valid_csrf:
            alert = "<div class='alert alert-error'>Verification failed: Invalid or expired CSRF token. Please refresh the page.</div>"
        else:
            expected_email = VALID_RECORDS.get((school, student_id))
            if expected_email and expected_email.lower() == email.lower():
                alert = f"<div class='alert alert-success'>SUCCESS: Sign-up successful! Welcome to the portal, {student_id}!</div>"
            else:
                alert = "<div class='alert alert-error'>Error: Student record not found or ID and email do not match for this school.</div>"

        html = HTML_TEMPLATE.replace("{ALERT_BLOCK}", alert).replace("{CSRF_TOKEN}", new_csrf)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Set-Cookie", f"session_id={new_session_id}; Path=/; HttpOnly")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

def run_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), PortalHandler)
    print(f"[*] Mock Digital Learning Portal running on http://127.0.0.1:{port}")
    print("[*] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping mock server.")
        server.server_close()

if __name__ == "__main__":
    run_server()
