import os
import importlib
from pathlib import Path

from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer

import app as simt

def test_pages_and_links(tmp_path, monkeypatch):
    monkeypatch.setattr(simt, "DB_PATH", tmp_path / "simt.sqlite")
    simt.init_db()
    client = TestClient(simt.app)
    urls = ["/","/about","/services","/who-we-help","/approach","/concept-projects",
            "/concept-projects/cafe-lahore","/concept-projects/clothing-brand-launch",
            "/concept-projects/food-for-students","/concept-projects/local-beauty-product",
            "/contact","/privacy","/health"]
    for url in urls:
        r = client.get(url)
        assert r.status_code == 200, (url, r.text[:200])
    assert client.get("/concept-projects/not-a-real-study").status_code == 404
    assert b"simt.consultancy007@gmail.com" in client.get("/contact").content
    assert b"hello@simt.example" not in client.get("/").content
    assert b"Concept only" in client.get("/concept-projects/cafe-lahore").content
    contact_html = client.get("/contact").text
    assert "calendly.com/simt-consultancy007/30min" in contact_html
    assert "Book a 30-minute SIMT Strategy Consultation with Calendly" in contact_html
    assert "linkedin.com/company/simt-marketing" in client.get("/").text
    about_html = client.get("/about").text
    for member in ("Umm-E-Abeeha", "Mohsin Umar", "Aneesa Riaz"):
        assert member in about_html
    assert b"WhatsApp" in client.get("/contact").content
    # No bogus WhatsApp href until actual number configured
    assert 'href="https://wa.me/' not in client.get("/contact").text

def test_inquiry_stores_then_admin_can_manage(tmp_path,monkeypatch):
    monkeypatch.setattr(simt, "DB_PATH", tmp_path / "tests.sqlite")
    monkeypatch.setattr(simt, "SMTP_HOST", "")
    monkeypatch.setattr(simt, "ADMIN_PASSWORD", "An-Unpredictable-Long-Password-231")
    monkeypatch.setattr(simt, "_signer", URLSafeTimedSerializer("random-long-independent-session-secret",salt="simt-admin"))
    simt._rate.clear()
    simt.init_db()
    client=TestClient(simt.app)
    payload = {
        "kind":"consultation","name":"Potential Customer","email":"buyer@example.com",
        "company":"Example Co","audience":"smes","service":"market-research",
        "message":"We would like to discuss a market-entry opportunity.",
        "preferred_date":"2026-12-05","website":""
    }
    r=client.post("/api/inquiries",json=payload)
    assert r.status_code==201, r.text
    ref=r.json()["reference"]
    assert ref
    with simt.db() as conn:
        row=conn.execute("select * from inquiries where id=?",(ref,)).fetchone()
        assert row["email"]=="buyer@example.com"
        assert row["notification_status"]=="not_configured"
        assert row["kind"]=="consultation"
    assert client.get("/admin", follow_redirects=False).status_code==303
    assert client.post("/admin/login",data={"password":"wrong"}).status_code==401
    login=client.post("/admin/login",data={"password":"An-Unpredictable-Long-Password-231"},follow_redirects=False)
    assert login.status_code==303
    response=client.get("/admin")
    assert response.status_code==200
    assert ref in response.text
    assert "buyer@example.com" in response.text
    set_status=client.post(f"/admin/inquiries/{ref}/status",data={"status":"contacted"}, follow_redirects=False)
    assert set_status.status_code==303
    with simt.db() as conn:
        assert conn.execute("select status from inquiries where id=?",(ref,)).fetchone()[0]=="contacted"

def test_validation_and_xss(tmp_path,monkeypatch):
    monkeypatch.setattr(simt, "DB_PATH", tmp_path / "test_validation.sqlite")
    simt._rate.clear()
    simt.init_db()
    client=TestClient(simt.app)
    invalid={"kind":"inquiry","name":"R","email":"notvalid","message":"tiny"}
    r=client.post("/api/inquiries",json=invalid)
    assert r.status_code==422
    valid={"kind":"inquiry","name":"Someone","email":"person@example.com",
           "message":"<script>alert('danger')</script> Could you help plan a launch?"}
    r=client.post("/api/inquiries",json=valid)
    assert r.status_code==201
    with simt.db() as conn:
        assert conn.execute("select count(*) from inquiries").fetchone()[0]==1
    assert client.post("/api/inquiries",json=valid,headers={"Origin":"https://evil.example.com"}).status_code==403
