import pytest

from jobapply.errors import JobapplyError
from jobapply.forms import Resolver


def test_waived_cover_letter_cannot_be_uploaded(application):
    application.data["cover_letter"] = False
    application.save()
    resolver = Resolver(application)
    with pytest.raises(JobapplyError, match="waives the cover letter"):
        resolver.resolve("document:cover_letter", {})
    files = resolver.resolve("attachments:all+documents", {})
    assert [p.name for p in files][:1] == [application.document_paths()["cv"].name]
    assert len(files) == 5
