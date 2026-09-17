"""The `email` step: compose the message a by-email Application is sent with.

An employer that offers no Form but an address (``"form_url": "mailto:..."`` in
application.json) gets a short covering email with the Dossier attached. The
tool writes the message to ``email.md``, hands it to the applicant's mail client
through a ``mailto:`` URL and names the file to attach; the applicant attaches it
and presses send. Attachments cannot travel in a mailto: URL, so that part is
always the applicant's.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .application import Application
from .errors import JobapplyError
from .render import build_salutation, build_subject


@dataclass
class Email:
    to: str
    subject: str
    body: str
    attachments: list[Path]

    def mailto_url(self) -> str:
        return f"mailto:{self.to}?subject={quote(self.subject)}&body={quote(self.body)}"

    def as_markdown(self) -> str:
        files = "\n".join(f"- {p}" for p in self.attachments)
        return (f"To: {self.to}\nSubject: {self.subject}\n\n{self.body}\n\n"
                f"Attach:\n{files}\n")


def compose_email(app: Application) -> Email:
    """Subject and salutation as on the letter, the fixed ``email_body`` paragraphs from
    cover-letter.<lang>.json, then sign-off, name and phone from the Profile."""
    if not app.applies_by_email:
        raise JobapplyError(f'{app.slug} has a web Form, not an email address (application.json "form_url")')
    lang = app.language
    fixed = lang.resolve(app.workspace.cover_letter_fixed(lang.code), f"cover-letter.{lang.code}.json")
    posting = lang.resolve(app.posting(), "posting")
    profile = lang.resolve(app.profile(), "profile")
    paragraphs = fixed.get("email_body")
    if not paragraphs:
        raise JobapplyError(
            f'cover-letter.{lang.code}.json has no "email_body": add the paragraphs of the covering email '
            f'(placeholders: {{role}}, {{company}}, {{reference}}).'
        )
    letter = app.cover_letter()
    subject = build_subject(letter, fixed, posting)
    body = [build_salutation(letter, fixed, posting), ""]
    for text in paragraphs:
        body += [text.format(role=posting.get("role", ""), company=posting.get("company", ""),
                             reference=posting.get("reference", "")), ""]
    body += [fixed.get("sign_off", ""), f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()]
    phone = (profile.get("contact") or {}).get("phone", "")
    if phone:
        body.append(phone)
    docs = app.document_paths()
    return Email(to=app.application_email, subject=subject, body="\n".join(body), attachments=[docs["merged"]])


def write_email(app: Application) -> Email:
    """Compose and store email.md; the Dossier must be rendered first."""
    email = compose_email(app)
    missing = [p for p in email.attachments if not p.exists()]
    if missing:
        raise JobapplyError(f"Render first; not found: {', '.join(p.name for p in missing)}")
    app.email_path.write_text(email.as_markdown(), encoding="utf-8")
    return email


def open_mail_client(email: Email) -> None:
    """Hand to, subject and body to the desktop mail client; attachments are the applicant's."""
    import subprocess

    try:
        subprocess.Popen(["xdg-open", email.mailto_url()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        raise JobapplyError(f"Could not open the mail client; write the email from {email.to} by hand") from None
