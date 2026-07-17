from app.main import app


def test_api_has_general_release_assurance_title():
    assert app.title == "Release Assurance API"
