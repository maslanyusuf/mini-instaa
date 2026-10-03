# Django Email Guide: Localhost to Production

A complete guide to sending, testing, and deploying emails in Django.

## Table of Contents

1. [How Django Email Works](#1-how-django-email-works)
2. [Localhost Setup](#2-localhost-setup)
3. [Sending Emails (Code Examples)](#3-sending-emails-code-examples)
4. [Testing Emails](#4-testing-emails)
5. [Environment-Based Settings](#5-environment-based-settings)
6. [Production Setup](#6-production-setup)
7. [Email Providers Cheat Sheet](#7-email-providers-cheat-sheet)
8. [Deliverability: SPF, DKIM, DMARC](#8-deliverability-spf-dkim-dmarc)
9. [Background Sending with Celery](#9-background-sending-with-celery)
10. [Error Emails to Admins](#10-error-emails-to-admins)
11. [Troubleshooting](#11-troubleshooting)
12. [Production Checklist](#12-production-checklist)

---

## 1. How Django Email Works

Django sends mail through an **email backend**, selected by the `EMAIL_BACKEND` setting. Your code stays the same (`send_mail(...)`); only the backend changes between environments.

| Backend                  | Use for                           | What it does                                                             |
| ------------------------ | --------------------------------- | ------------------------------------------------------------------------ |
| `console.EmailBackend`   | Local dev                         | Prints the email to your terminal                                        |
| `filebased.EmailBackend` | Local dev                         | Saves each email as a `.log` file                                        |
| `smtp.EmailBackend`      | Local debug server and production | Sends through an SMTP server                                             |
| `locmem.EmailBackend`    | Tests                             | Stores emails in `mail.outbox` (Django sets this automatically in tests) |
| `dummy.EmailBackend`     | Disabling email                   | Does nothing                                                             |
| Anymail backends         | Production                        | Sends through provider HTTP APIs (SendGrid, Mailgun, SES, ...)           |

All backends live under `django.core.mail.backends.`.

---

## 2. Localhost Setup

### Option A: Console backend (simplest)

Emails print in the terminal where `runserver` is running. No server needed.

```python
# settings.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@localhost.com"
```

### Option B: File backend

Saves every email to a file so you can inspect it later.

```python
# settings.py
EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = BASE_DIR / "sent_emails"  # folder is created automatically
DEFAULT_FROM_EMAIL = "noreply@localhost.com"
```

Add `sent_emails/` to `.gitignore`.

### Option C: Local SMTP debug server

Behaves like a real SMTP server, so you test the same code path as production.

```python
# settings.py
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "noreply@localhost.com"
```

Start the debug server in a **separate terminal**:

```bash
# Python 3.11 and older
python -m smtpd -n -c DebuggingServer localhost:1025

# Python 3.12+ (smtpd was removed from the standard library)
pip install aiosmtpd
python -m aiosmtpd -n -l localhost:1025
```

> The port in `settings.py` must match the port the server listens on. If you get `ConnectionRefusedError`, nothing is listening on that port.

### Option D: Mailpit (recommended: a real inbox UI)

[Mailpit](https://mailpit.axllent.org) catches all SMTP mail and shows it in a web inbox, including HTML rendering, attachments, and headers.

```bash
docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit
```

- SMTP: `localhost:1025` (use the same settings as Option C)
- Web UI: http://localhost:8025

MailHog and Mailtrap work the same way. Mailtrap is hosted and gives you an SMTP host, user, and password to paste into settings.

---

## 3. Sending Emails (Code Examples)

### 3.1 Quick test from the shell

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail

send_mail(
    subject="Test Email from Django",
    message="Hello! This is a test email.",
    from_email=None,  # falls back to DEFAULT_FROM_EMAIL
    recipient_list=["test@example.com"],
    fail_silently=False,
)
```

`send_mail` returns the number of emails sent (`1` on success).

### 3.2 HTML email with a plain-text fallback

```python
from django.core.mail import EmailMultiAlternatives

msg = EmailMultiAlternatives(
    subject="Welcome!",
    body="Welcome to our site.",  # plain-text version
    from_email="noreply@localhost.com",
    to=["test@example.com"],
    cc=["cc@example.com"],
    reply_to=["support@example.com"],
)
msg.attach_alternative("<h1>Welcome!</h1><p>Thanks for signing up.</p>", "text/html")
msg.send()
```

### 3.3 Using Django templates (best practice)

```
templates/
└── emails/
    ├── welcome.html
    └── welcome.txt
```

```html
<!-- templates/emails/welcome.html -->
<h1>Hi {{ user.first_name }}!</h1>
<p>Welcome to {{ site_name }}.</p>
<a href="{{ login_url }}">Log in</a>
```

```text
{# templates/emails/welcome.txt #}
Hi {{ user.first_name }}!
Welcome to {{ site_name }}.
Log in: {{ login_url }}
```

```python
# emails.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_welcome_email(user):
    context = {
        "user": user,
        "site_name": "MySite",
        "login_url": f"{settings.SITE_URL}/login/",
    }
    text_body = render_to_string("emails/welcome.txt", context)
    html_body = render_to_string("emails/welcome.html", context)

    msg = EmailMultiAlternatives(
        subject="Welcome to MySite",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
```

Add `SITE_URL = "http://127.0.0.1:8000"` locally and your real domain in production.

### 3.4 Attachments

```python
from pathlib import Path
from django.conf import settings

msg.attach_file(Path(settings.BASE_DIR) / "media" / "invoice.pdf")

# Or attach in-memory content
msg.attach("report.csv", csv_string, "text/csv")
```

### 3.5 Sending from a view

```python
# views.py
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse


def send_test_email(request):
    send_mail(
        subject="Django Test",
        message="It works!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["test@example.com"],
        fail_silently=False,
    )
    return HttpResponse("Email sent! Check your terminal or inbox.")
```

```python
# urls.py
from django.urls import path
from .views import send_test_email

urlpatterns = [
    path("send-email/", send_test_email),
]
```

Visit http://127.0.0.1:8000/send-email/.

### 3.6 Sending many emails over one connection

```python
from django.core import mail

connection = mail.get_connection()
connection.open()

messages = [
    mail.EmailMessage(f"Hello {n}", "Body", "noreply@example.com", [addr])
    for n, addr in enumerate(["a@example.com", "b@example.com"])
]
connection.send_messages(messages)
connection.close()
```

`send_mass_mail()` also exists, but `get_connection()` with `EmailMessage` objects is more flexible.

### 3.7 Built-in emails: password reset

Django's auth views already send mail. Make sure your email settings work and these are configured:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
]
```

Locally, the reset link appears in your console or Mailpit inbox.

---

## 4. Testing Emails

During `manage.py test`, Django automatically swaps in the in-memory backend, so no real mail is sent.

```python
from django.test import TestCase
from django.core import mail


class EmailTest(TestCase):
    def test_send_email(self):
        mail.send_mail(
            "Subject here",
            "Here is the message.",
            "from@example.com",
            ["to@example.com"],
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Subject here")
        self.assertEqual(mail.outbox[0].to, ["to@example.com"])
```

Test an email triggered by a view:

```python
def test_signup_sends_welcome_email(self):
    response = self.client.post("/signup/", {"email": "new@example.com", "password": "pass12345"})
    self.assertEqual(response.status_code, 302)
    self.assertEqual(len(mail.outbox), 1)
    self.assertIn("Welcome", mail.outbox[0].subject)
```

Run:

```bash
python manage.py test
```

---

## 5. Environment-Based Settings

Never hardcode credentials. Read them from environment variables.

```bash
pip install python-dotenv
```

```env
# .env (local development) - add to .gitignore!
DEBUG=True
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@localhost.com
SITE_URL=http://127.0.0.1:8000
```

```env
# .env (production, or set these in your host's dashboard)
DEBUG=False
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-secret-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=MySite <noreply@yourdomain.com>
SITE_URL=https://yourdomain.com
```

```python
# settings.py
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 1025))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
EMAIL_TIMEOUT = 10  # seconds; prevents requests hanging on a dead server
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@localhost.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)  # sender for error emails
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000")
```

Defaulting to the console backend means a missing variable never accidentally sends real mail from a dev machine.

---

## 6. Production Setup

### 6.1 Choose a transport: SMTP or API

**SMTP**: works with any provider, no extra packages. Good starting point.

**API via [django-anymail](https://anymail.dev)**: uses the provider's HTTP API. Gives you delivery status, webhooks (bounces, opens, clicks), message IDs, and templates. Better for serious production use.

### 6.2 SMTP in production

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.yourprovider.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = "your-username"
EMAIL_HOST_PASSWORD = "your-secret"  # load from env!
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = "MySite <noreply@yourdomain.com>"
```

**TLS vs SSL**

| Port | Setting                | Notes                          |
| ---- | ---------------------- | ------------------------------ |
| 587  | `EMAIL_USE_TLS = True` | STARTTLS. The modern default.  |
| 465  | `EMAIL_USE_SSL = True` | Implicit TLS.                  |
| 25   | none                   | Often blocked by hosts; avoid. |

`EMAIL_USE_TLS` and `EMAIL_USE_SSL` are **mutually exclusive**. Setting both raises an error.

### 6.3 API backend with django-anymail (SendGrid example)

```bash
pip install "django-anymail[sendgrid]"
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "anymail",
]

EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
ANYMAIL = {
    "SENDGRID_API_KEY": os.getenv("SENDGRID_API_KEY"),
}
DEFAULT_FROM_EMAIL = "MySite <noreply@yourdomain.com>"
SERVER_EMAIL = "server@yourdomain.com"
```

Your `send_mail` and `EmailMultiAlternatives` code does not change. Other backends: `anymail.backends.mailgun.EmailBackend`, `amazon_ses`, `postmark`, `brevo`, `resend`, and more. See the Anymail docs for each provider's extras and setting names.

Reading delivery info after sending:

```python
msg.send()
print(msg.anymail_status.message_id)
print(msg.anymail_status.status)  # {'queued'} / {'sent'} / ...
```

### 6.4 Gmail SMTP (small projects only)

Gmail is fine for a hobby project but limited (roughly 500 recipients/day) and can block sign-ins.

1. Enable **2-Step Verification** on the Google account.
2. Create an **App Password** (Google Account → Security → App passwords).
3. Use that 16-character password, not your normal one.

```python
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "you@gmail.com"
EMAIL_HOST_PASSWORD = "your-app-password"
DEFAULT_FROM_EMAIL = "you@gmail.com"  # Gmail rewrites other From addresses
```

Use a dedicated transactional provider for anything with real users.

### 6.5 Hosting notes

- Many cloud hosts (DigitalOcean, AWS EC2, GCP, some PaaS plans) **block outbound port 25**. Use 587 or 465, or an API backend.
- Set secrets as environment variables in your host's dashboard (Render, Railway, Heroku, Fly.io, etc.), not in the repo.
- Use a real domain you control for `DEFAULT_FROM_EMAIL`. Sending from `@gmail.com` or `@localhost` through a third-party provider gets rejected or spam-foldered.

---

## 7. Email Providers Cheat Sheet

Verify details in each provider's dashboard, since hosts and policies change.

| Provider           | SMTP host                           | Port | Username                     | Password      |
| ------------------ | ----------------------------------- | ---- | ---------------------------- | ------------- |
| SendGrid           | `smtp.sendgrid.net`                 | 587  | literal `apikey`             | your API key  |
| Mailgun            | `smtp.mailgun.org`                  | 587  | SMTP login from dashboard    | SMTP password |
| Amazon SES         | `email-smtp.<region>.amazonaws.com` | 587  | SMTP username (not IAM user) | SMTP password |
| Postmark           | `smtp.postmarkapp.com`              | 587  | Server API token             | same token    |
| Brevo (Sendinblue) | `smtp-relay.brevo.com`              | 587  | account login                | SMTP key      |
| Gmail              | `smtp.gmail.com`                    | 587  | full address                 | App Password  |

**Free tiers and sandboxes:** Amazon SES starts in sandbox mode (you can only send to verified addresses until you request production access). Most providers require verifying your sender domain or address before sending.

---

## 8. Deliverability: SPF, DKIM, DMARC

Without these DNS records, your production email will likely land in spam or be rejected.

| Record    | Purpose                                                    | Typical form                                                                        |
| --------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| **SPF**   | Lists servers allowed to send for your domain              | TXT: `v=spf1 include:sendgrid.net ~all`                                             |
| **DKIM**  | Cryptographic signature proving the message wasn't altered | CNAME/TXT records the provider gives you                                            |
| **DMARC** | Policy for what to do when SPF/DKIM fail, plus reporting   | TXT at `_dmarc.yourdomain.com`: `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` |

Steps:

1. Add your domain in the provider dashboard.
2. Copy the DNS records they give you into your DNS host.
3. Wait for verification (minutes to hours).
4. Start DMARC at `p=none`, review reports, then tighten to `quarantine` or `reject`.
5. Test with [mail-tester.com](https://www.mail-tester.com) or Google Postmaster Tools.

Good practices:

- Always include a plain-text alternative alongside HTML.
- Use a consistent, recognizable From name and address.
- Add an unsubscribe link for marketing mail.
- Separate transactional mail (password resets) from bulk/marketing mail, ideally on different sender domains or streams.

---

## 9. Background Sending with Celery

Sending email inside a request blocks the response and fails if the mail server is slow. Move it to a background task in production.

```bash
pip install celery redis
```

```python
# myproject/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# myproject/__init__.py
from .celery import app as celery_app

__all__ = ("celery_app",)
```

```python
# settings.py
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
```

```python
# accounts/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from .emails import send_welcome_email


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_welcome_email_task(self, user_id):
    user = get_user_model().objects.get(pk=user_id)
    send_welcome_email(user)
```

```python
# views.py
from django.db import transaction
from .tasks import send_welcome_email_task


def signup(request):
    # ... create user ...
    transaction.on_commit(lambda: send_welcome_email_task.delay(user.id))
```

Notes:

- Pass **IDs**, not model instances, to tasks.
- `transaction.on_commit` ensures the task doesn't run before the user row exists.
- Run the worker: `celery -A myproject worker -l info`.
- Lighter alternatives: `django-q2`, `huey`, or Django 6.0's built-in tasks framework if you're on it.

---

## 10. Error Emails to Admins

With `DEBUG=False`, Django can email you tracebacks for unhandled 500 errors.

```python
ADMINS = [("Your Name", "you@yourdomain.com")]
MANAGERS = ADMINS
SERVER_EMAIL = "server@yourdomain.com"  # From address for these emails
EMAIL_SUBJECT_PREFIX = "[MySite] "
```

Test it:

```bash
python manage.py sendtestemail --admins
python manage.py sendtestemail someone@example.com
```

`sendtestemail` is a handy built-in command for verifying your production config without writing code.

Consider Sentry for error tracking at scale, since admin emails get noisy.

---

## 11. Troubleshooting

| Symptom                                                   | Likely cause and fix                                                                        |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `ConnectionRefusedError: [Errno 111]`                     | Nothing is listening on `EMAIL_HOST:EMAIL_PORT`. Start the debug server or fix the port.    |
| `smtplib.SMTPServerDisconnected`                          | Wrong TLS/SSL combination for the port. 587 → TLS, 465 → SSL.                               |
| `SMTPAuthenticationError (535)`                           | Wrong credentials. Gmail needs an App Password. SendGrid username must be `apikey`.         |
| `SMTPSenderRefused` / `550`                               | From address or domain isn't verified with the provider.                                    |
| `ssl.SSLError: WRONG_VERSION_NUMBER`                      | You enabled SSL on a STARTTLS port (or vice versa).                                         |
| `TimeoutError` / request hangs                            | Port blocked by your host, or firewall. Try 587/465 or an API backend. Set `EMAIL_TIMEOUT`. |
| Emails go to spam                                         | Missing SPF/DKIM/DMARC, or the From domain doesn't match the authenticated domain.          |
| Emails don't arrive, no error                             | You're still on the console/file backend, or `fail_silently=True` is hiding errors.         |
| `ImproperlyConfigured: ...TLS/SSL are mutually exclusive` | Set only one of `EMAIL_USE_TLS` / `EMAIL_USE_SSL`.                                          |
| Env var booleans always `True`                            | `bool("False")` is `True`. Compare strings: `os.getenv("X") == "True"`.                     |

Debugging tips:

```python
# See the raw SMTP conversation
import smtplib
smtplib.SMTP.debuglevel = 1
```

Or check where mail is going:

```python
from django.conf import settings
print(settings.EMAIL_BACKEND, settings.EMAIL_HOST, settings.EMAIL_PORT)
```

---

## 12. Production Checklist

- [ ] `EMAIL_BACKEND` is SMTP or an Anymail backend (not console/file)
- [ ] Credentials come from environment variables, not source control
- [ ] `.env` is in `.gitignore`
- [ ] `DEFAULT_FROM_EMAIL` uses a domain you own
- [ ] Sender domain verified with the provider
- [ ] SPF, DKIM, and DMARC records published
- [ ] `EMAIL_TIMEOUT` set
- [ ] `EMAIL_USE_TLS` **or** `EMAIL_USE_SSL`, never both
- [ ] Emails sent from background tasks, with retries
- [ ] HTML emails include a plain-text alternative
- [ ] `SITE_URL` points to the production domain (links in emails are correct)
- [ ] `ADMINS` and `SERVER_EMAIL` configured for error reports
- [ ] Verified with `python manage.py sendtestemail you@yourdomain.com`
- [ ] Spam score checked (mail-tester.com)
- [ ] Bounce/complaint handling set up (Anymail webhooks or provider dashboard)
- [ ] Provider rate limits and sandbox restrictions understood

---

## Quick Reference

```python
# Simple
send_mail(subject, message, from_email, [to], fail_silently=False)

# HTML + text
msg = EmailMultiAlternatives(subject, text, from_email, [to])
msg.attach_alternative(html, "text/html")
msg.send()

# Test
from django.core import mail
mail.outbox  # list of sent messages during tests

# CLI check
python manage.py sendtestemail you@example.com
```
