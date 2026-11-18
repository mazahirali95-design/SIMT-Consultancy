"""
SIMT full-stack consultancy website.
FastAPI serves responsive Jinja pages and handles real inquiry storage and
optional SMTP alerts. No customer message is silently discarded.
"""
from __future__ import annotations

import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from content import PROJECTS, SERVICES, AUDIENCES, STEPS

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "simt.sqlite3")))
SIMT_EMAIL = os.getenv("SIMT_EMAIL", "simt.consultancy007@gmail.com").strip()
WHATSAPP_NUMBER = re.sub(r"\D", "", os.getenv("WHATSAPP_NUMBER", ""))
CALENDLY_URL = os.getenv("CALENDLY_URL", "https://calendly.com/simt-consultancy007/30min").strip()
LINKEDIN_URL = "https://www.linkedin.com/company/simt-marketing"
TEAM_MEMBERS = [
    {"name": "SIMT Founder", "role": "Role and biography to be added", "bio": "Founder profile details will be added when supplied."},
    {"name": "Umm-E-Abeeha", "role": "Role and biography to be added", "bio": "Profile details will be added when supplied."},
    {"name": "Mohsin Umar", "role": "Role and biography to be added", "bio": "Profile details will be added when supplied."},
    {"name": "Aneesa Riaz", "role": "Role and biography to be added", "bio": "Profile details will be added when supplied."},
]
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() != "false"
app = FastAPI(title="SIMT | Direction That Drives Growth", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.autoescape = True
_lock = threading.RLock()
_rate: dict[str, deque[float]] = defaultdict(deque)
_salt = "simt-admin"
_signer = URLSafeTimedSerializer(SESSION_SECRET, salt=_salt) if SESSION_SECRET else None

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          name TEXT NOT NULL,
          email TEXT NOT NULL,
          company TEXT NOT NULL DEFAULT '',
          audience TEXT NOT NULL DEFAULT '',
          service TEXT NOT NULL DEFAULT '',
          message TEXT NOT NULL,
          preferred_date TEXT NOT NULL DEFAULT '',
          status TEXT NOT NULL DEFAULT 'new',
          notification_status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_inquiries_created ON inquiries(created_at DESC)")
        conn.commit()

init_db()

def site_context(request: Request, **kwargs):
    return {
        "request": request,
        "site_email": SIMT_EMAIL,
        "whatsapp": f"https://wa.me/{WHATSAPP_NUMBER}?text=Hello%20SIMT%2C%20I%27d%20like%20to%20discuss%20my%20business." if WHATSAPP_NUMBER else None,
        "calendly": CALENDLY_URL if CALENDLY_URL.startswith("https://calendly.com/") else None,
        "linkedin": LINKEDIN_URL,
        "team_members": TEAM_MEMBERS,
        "services": SERVICES,
        "audiences": AUDIENCES,
        "steps": STEPS,
        "projects": PROJECTS,
        "year": datetime.now(timezone.utc).year,
        **kwargs
    }

def page(request, template, title, description, **kwargs):
    return templates.TemplateResponse(
        request=request, name=template,
        context=site_context(request, page_title=title, page_description=description, **kwargs)
    )

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return page(request, "home.html", "Strategic Marketing & Market-Entry Consultancy", "SIMT guides founders and businesses with customer insights, market-entry feasibility and practical marketing strategy.", active="home")

@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return page(request, "about.html", "About SIMT", "Meet SIMT's perspective, mission and four complementary consultancy roles.", active="about")

@app.get("/services", response_class=HTMLResponse)
def services_page(request: Request):
    return page(request, "services.html", "Services", "Explore SIMT's eight marketing, market-entry and business strategy services.", active="services")

@app.get("/who-we-help", response_class=HTMLResponse)
def who(request: Request):
    return page(request, "who.html", "Who We Help", "Dedicated strategic consultancy support for startups, SMEs and large companies.", active="who")

@app.get("/approach", response_class=HTMLResponse)
def approach(request: Request):
    return page(request, "approach.html", "Our Approach", "Discover how SIMT moves from understanding a question to making a practical recommendation.", active="approach")

@app.get("/concept-projects", response_class=HTMLResponse)
def concept(request: Request):
    return page(request, "projects.html", "Concept Projects", "Four illustrative studies showing how SIMT might research and plan for different business challenges.", active="projects")

@app.get("/concept-projects/{slug}", response_class=HTMLResponse)
def project(request: Request, slug: str):
    project_data = next((p for p in PROJECTS if p["slug"] == slug), None)
    if not project_data:
        raise HTTPException(404, "Concept project not found")
    return page(request, "project_detail.html", project_data["title"], project_data["summary"], active="projects", project=project_data)

@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return page(request, "contact.html", "Contact & Consultation", "Send SIMT a business inquiry or request a consultation, with optional WhatsApp and Calendly connections.", active="contact")

@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return page(request, "privacy.html", "Privacy Notice", "Learn about the personal information SIMT collects through its inquiry and consultation forms.", active="privacy")

def rate_limit(key: str, n: int, seconds: int) -> bool:
    now = time.monotonic()
    with _lock:
        q = _rate[key]
        while q and now - q[0] > seconds:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        return True

def origin_valid(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True  # non-browser clients need not send an Origin
    parsed = urlparse(origin)
    return parsed.scheme in ("http", "https") and parsed.netloc == request.headers.get("host")

def notify_inbox(record: dict) -> str:
    if not (SMTP_HOST and SMTP_FROM):
        return "not_configured"
    msg = EmailMessage()
    msg["Subject"] = f"[SIMT] {record['kind'].title()} — {record['name']} ({record['id']})"
    msg["From"] = SMTP_FROM
    msg["To"] = SIMT_EMAIL
    # Reply-To verified only by form validation, not authenticated;
    # avoid using it to prevent sender-spoofing assumptions.
    msg.set_content(
        f"New SIMT {record['kind']} — {record['id']}\n\n"
        f"Name: {record['name']}\nEmail: {record['email']}\n"
        f"Company: {record['company']}\nAudience: {record['audience']}\n"
        f"Service: {record['service']}\nPreferred date: {record['preferred_date']}\n\n"
        f"Message:\n{record['message']}\n\n"
        "Review this inquiry in the protected SIMT admin dashboard."
    )
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=9) as server:
            if SMTP_STARTTLS:
                server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return "sent"
    except Exception:
        # The inquiry remains stored. Do not disclose SMTP credentials to visitors.
        return "failed"

@app.post("/api/inquiries")
async def new_inquiry(request: Request):
    if not origin_valid(request):
        raise HTTPException(status_code=403, detail="Invalid request origin.")
    try:
        length = int(request.headers.get("content-length", "0"))
    except ValueError:
        length = 0
    if length > 14000:
        raise HTTPException(status_code=413, detail="Submission is too large.")
    ip = request.client.host if request.client else "unknown"
    if not rate_limit("inquiry:" + ip, 6, 900):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form submission.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid form submission.")
    if payload.get("website"):  # honeypot field
        return JSONResponse(status_code=200, content={"ok": True, "reference": "received"})
    fields = ("kind", "name", "email", "company", "audience", "service", "message", "preferred_date")
    if any(not isinstance(payload.get(f, ""), str) for f in fields):
        raise HTTPException(status_code=422, detail="Invalid field values.")
    value = {key: payload.get(key, "").strip() for key in fields}
    value["email"] = value["email"].lower()
    if value["kind"] not in ("inquiry", "consultation"):
        raise HTTPException(422, "Choose an inquiry type.")
    if not 2 <= len(value["name"]) <= 100:
        raise HTTPException(422, "Please enter your name (2–100 characters).")
    if len(value["email"]) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value["email"]):
        raise HTTPException(422, "Please enter a valid email.")
    if not 12 <= len(value["message"]) <= 3000:
        raise HTTPException(422, "Please describe your request (12–3000 characters).")
    if any(len(value[f]) > lim for f,lim in (("company",140),("audience",80),("service",120),("preferred_date",30))):
        raise HTTPException(422, "One of the fields is too long.")
    if value["kind"] == "consultation" and value["preferred_date"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value["preferred_date"]):
        raise HTTPException(422, "Invalid preferred date.")
    value.update(id=secrets.token_hex(6).upper(), created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with db() as conn:
        conn.execute("""INSERT INTO inquiries
          (id, kind, name, email, company, audience, service, message, preferred_date, created_at)
          VALUES (:id,:kind,:name,:email,:company,:audience,:service,:message,:preferred_date,:created_at)""", value)
        conn.commit()
    notification = notify_inbox(value)
    with db() as conn:
        conn.execute("UPDATE inquiries SET notification_status=? WHERE id=?", (notification, value["id"]))
        conn.commit()
    return JSONResponse(status_code=201, content={
        "ok": True, "reference": value["id"],
        "message": "Your request has been received. SIMT will follow up using the details provided."
    })

def admin_enabled():
    return bool(_signer and ADMIN_PASSWORD and len(ADMIN_PASSWORD) >= 12)

def admin_authorized(request: Request):
    if not admin_enabled():
        return False
    cookie = request.cookies.get("simt_admin", "")
    try:
        return _signer.loads(cookie, max_age=60 * 60 * 8) == "authenticated"
    except (BadSignature, SignatureExpired):
        return False

@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    return page(request, "admin_login.html", "Admin Sign In", "Restricted access.", active="admin", admin_ready=admin_enabled(), login_error="")

@app.post("/admin/login")
def login_submit(request: Request, password: str = Form(...)):
    if not origin_valid(request):
        raise HTTPException(403)
    ip = request.client.host if request.client else "unknown"
    if not rate_limit("admin:" + ip, 8, 900):
        raise HTTPException(429, "Too many login attempts.")
    if not admin_enabled() or not hmac.compare_digest(password, ADMIN_PASSWORD):
        return templates.TemplateResponse(request=request, name="admin_login.html", status_code=401,
            context=site_context(request, active="admin", page_title="Admin Sign In",
                page_description="Restricted access.", admin_ready=admin_enabled(), login_error="Invalid login or admin configuration."))
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("simt_admin", _signer.dumps("authenticated"), httponly=True,
                        samesite="strict", secure=request.url.scheme=="https",
                        max_age=8*60*60)
    return response

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not admin_authorized(request):
        return RedirectResponse("/admin/login", status_code=303)
    with db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 300")]
        counts = {r["status"]:r["n"] for r in conn.execute("SELECT status, COUNT(*) AS n FROM inquiries GROUP BY status")}
    return page(request, "admin.html", "Inquiry Dashboard", "Protected SIMT admin", active="admin", inquiries=rows, counts=counts)

@app.post("/admin/inquiries/{item_id}/status")
def set_status(request: Request, item_id: str, status: str = Form(...)):
    if not admin_authorized(request) or not origin_valid(request):
        raise HTTPException(403, "Unauthorized.")
    if status not in ("new", "contacted", "closed"):
        raise HTTPException(422, "Invalid status.")
    with db() as conn:
        conn.execute("UPDATE inquiries SET status=? WHERE id=?", (status, item_id))
        conn.commit()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/logout")
def logout(request: Request):
    if not admin_authorized(request) or not origin_valid(request):
        raise HTTPException(403)
    response=RedirectResponse("/", status_code=303)
    response.delete_cookie("simt_admin")
    return response

@app.get("/health")
def health():
    return {"ok":True,"service":"SIMT website"}
