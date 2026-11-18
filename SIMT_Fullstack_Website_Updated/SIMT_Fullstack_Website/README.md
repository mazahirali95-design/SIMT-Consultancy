# SIMT — Independent Full-Stack Consultancy Website

A responsive full-stack site built to match SIMT's shared Emergent design references. It is **not** a copy of Emergent's source code. All content, logic and styling in this project can be edited without Emergent credits.

## Included

- Responsive pages: Home, About, Services, Who We Help, Our Approach, Concept Projects and **four detailed concept studies**, Contact, Privacy Notice.
- Original SIMT logo mark (cropped from the original uploaded image without redesigning) and the full original logo asset.
- Business inquiry form and **consultation-request** form (a request, **not** a confirmed appointment).
- Real FastAPI POST `/api/inquiries`: validates inputs, basic rate limiting + hidden honeypot, stores submissions in SQLite, returns a receipt reference.
- Optional SMTP notifications to `simt.consultancy007@gmail.com`.
- Password-protected admin dashboard at `/admin` to view submissions and mark as New / Contacted / Closed.
- SIMT LinkedIn company page linked in the site footer.
- About page includes the four supplied team names, with roles and biographies clearly marked for later completion.
- WhatsApp button appears when the actual number is configured.
- Calendly 30-minute booking calendar embedded on Contact, using SIMT's supplied booking link; the URL can be changed through `CALENDLY_URL`.
- Responsive mobile menu, keyboard-friendly interactive components, lightweight motion respecting reduced-motion preferences.
- No fake testimonial, client result, office address, WhatsApp number or booked appointment.

## Run on your computer

You need Python 3.10+ and a terminal:

```bash
cd SIMT_Fullstack_Website
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

Open **http://127.0.0.1:8000/**.

Use Control+C to stop it. The web server must stay running for the form to work.

## Admin dashboard

Use a separate terminal or hosting provider's Environment Variables section:

```bash
export ADMIN_PASSWORD='choose-a-unique-long-password-at-least-12-characters'
export SESSION_SECRET='choose-a-different-long-random-string'
uvicorn app:app --reload
```

For Windows PowerShell replace `export` with `$env:ADMIN_PASSWORD="..."`, etc.

Then visit **http://127.0.0.1:8000/admin**. Admin is **disabled by default** until BOTH credentials are supplied. Do not send these passwords to anyone or store them in JavaScript. The admin cookie is HttpOnly, SameSite=Strict and gets Secure on HTTPS requests.

## Inquiry notification email

The submission form **already works** locally: it validates and saves incoming inquiries into the SQLite database. In the admin dashboard you can see each one. Email delivery requires real SMTP credentials. Configure environment variables:

```bash
export SMTP_HOST='smtp.gmail.com'
export SMTP_PORT='587'
export SMTP_USERNAME='simt.consultancy007@gmail.com'
export SMTP_PASSWORD='your-email-provider-app-password-not-your-normal-password'
export SMTP_FROM='simt.consultancy007@gmail.com'
export SIMT_EMAIL='simt.consultancy007@gmail.com'
```

If using Gmail SMTP, check the current account requirements for app passwords (often requires two-step verification); support varies by account type. You may instead use a transactional mail provider and its SMTP settings. **Never** expose credentials in browser code, chat or GitHub.

If SMTP is not configured or fails, the inquiry remains saved with its notification status visible to administrators. The public form does **not** claim an email was delivered. Back up the database regularly.

## LinkedIn

The SIMT LinkedIn company page is linked in the site footer: `https://www.linkedin.com/company/simt-marketing`.

## WhatsApp (later)

Set `WHATSAPP_NUMBER` to your real international number **without the plus sign**, e.g. `92...`. The Contact link then appears automatically on all pages. Do not use the fake WhatsApp number in the reference PDF.

## Calendly

The Contact page now embeds SIMT's supplied 30-minute booking calendar: `https://calendly.com/simt-consultancy007/30min`. Visitors can select an available slot directly in the page, or open Calendly in a new tab. To change the event later, set `CALENDLY_URL` to the new real Calendly event URL.

## Team profiles and tutorial video

The About page now names the four team members supplied so far. Replace the pending role and biography text in `app.py` (`TEAM_MEMBERS`) when the team details are ready. No team photos have been fabricated.

The website's existing responsive layout already adapts to phone and desktop screens. The AI tutorial video itself still needs to be produced and supplied; no video file was included with the project upload, so this update does not pretend a finished tutorial exists.

## Deployment notes

1. Use a Python-capable web host supporting a long-running FastAPI process (or Docker container).
2. Configure HTTPS, secure environment variables and persistent storage for the SQLite database, or adapt it to a managed DB. A host with **ephemeral storage** may erase submitted leads between deploys or restarts — do not deploy SQLite there without a persistent volume.
3. Configure SMTP and test an inquiry from a different email account; verify arrival in SIMT's inbox and visibility in `/admin`.
4. Set a strong `ADMIN_PASSWORD` and independent `SESSION_SECRET` before public launch.
5. Configure WhatsApp, Calendly and a custom domain when ready. Prices and free-tier restrictions depend on hosting and vendors.
6. Consider stronger production controls for a public high-traffic site: managed Postgres, captcha/anti-bot service, automated database backups, admin multi-factor auth, request logging that excludes PII, and uptime monitoring.
7. Review the draft privacy notice for applicable legal requirements, actual data retention practices, host and email service before launch.
8. Images `home-consultancy.webp`, `about-architecture.webp` and `approach-research.webp` are *cropped from the reference PDFs the user supplied*; verify usage rights and replace with licensed originals before launch if necessary. The brand mark and full logo were cropped/copied from the original image provided by the user.

## Design / code guide

- `/templates/base.html` — navigation, footer, Google font references
- `/templates/home.html`, `about.html`, `services.html`, `who.html`, `approach.html`, `projects.html`, `project_detail.html`, `contact.html`, `privacy.html` — page layouts
- `/content.py` — all services, audience segments, six-step approach, four detailed concept studies
- `/static/css/site.css` — colors, typography, responsive layout, motion
- `/static/js/site.js` — mobile menu, form tabs, validation and API integration
- `/app.py` — page routes, form API, SQLite storage, optional SMTP, admin login/dashboard
- `/static/assets/simt-original-logo.webp` — unmodified full logo asset
- `/static/assets/simt-original-mark.png` — extracted original logo mark
- `/tests/` — API and page tests

## Run tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

**Status:** local full-stack functionality implemented and tested. No live deployment or real email provider is configured yet; Calendly/WhatsApp remain intentionally off until real details are supplied.
