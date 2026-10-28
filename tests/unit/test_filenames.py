from app.utils.filenames import (
    generate_internal_id,
    get_safe_extension,
    sanitize_display_filename,
)


def test_sanitize_strips_directories_and_control_chars():
    raw = "../../etc/pass\x00wd\nname.pdf"
    cleaned = sanitize_display_filename(raw)
    assert "/" not in cleaned
    assert "\x00" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.endswith(".pdf")


def test_sanitize_handles_windows_reserved_names():
    assert sanitize_display_filename("CON.pdf").startswith("_")
    assert sanitize_display_filename("LPT1").startswith("_")


def test_sanitize_truncates_long_names():
    raw = "a" * 400 + ".pdf"
    cleaned = sanitize_display_filename(raw)
    assert len(cleaned) <= 200
    assert cleaned.endswith(".pdf")


def test_sanitize_returns_untitled_for_empty():
    assert sanitize_display_filename("") == "untitled"
    assert sanitize_display_filename("....") in {"untitled", ""} or sanitize_display_filename("....") == "untitled"


def test_internal_id_is_random_and_url_safe():
    a, b = generate_internal_id(), generate_internal_id()
    assert a != b
    assert all(c.isalnum() or c in "-_" for c in a)


def test_get_safe_extension():
    assert get_safe_extension("foo.PDF") == ".pdf"
    assert get_safe_extension("foo") == ""
    assert get_safe_extension("foo.verylongextension") == ""