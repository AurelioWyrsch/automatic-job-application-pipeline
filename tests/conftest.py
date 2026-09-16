import json
from pathlib import Path

import pytest

from jobapply.application import Application
from jobapply.workspace import Workspace


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ws = Workspace.init(tmp_path / "ws")
    from pypdf import PdfWriter

    for name in ("zeugnis-a.pdf", "zeugnis-b.pdf", "diplom.pdf", "cert.pdf"):
        writer = PdfWriter()
        writer.add_blank_page(595, 842)
        with (ws.attachments_dir / name).open("wb") as fh:
            writer.write(fh)
    (ws.attachments_dir / "manifest.json").write_text(json.dumps({"attachments": [
        {"file": "cert.pdf", "kind": "certificate", "date": "2026-01", "title": "Cert"},
        {"file": "diplom.pdf", "kind": "diploma", "date": "2025-09", "title": {"de": "Diplom", "en": "Diploma"}},
        {"file": "zeugnis-a.pdf", "kind": "reference", "date": "2024-12", "title": "Zeugnis A"},
        {"file": "zeugnis-b.pdf", "kind": "reference", "date": "2025-06", "title": "Zeugnis B"},
    ]}), encoding="utf-8")
    return ws


@pytest.fixture
def application(workspace: Workspace) -> Application:
    return Application.create(
        workspace, company="Acme AG", role="Data Scientist", language="de",
        posting_url="https://example.com/job", form_url="https://example.com/apply",
    )
