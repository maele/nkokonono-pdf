from app.utils.validators import (
    parse_page_range,
    validate_image_file,
    validate_pdf_file,
)


def test_validate_pdf_accepts_magic_bytes(sample_pdf_path):
    ok, message = validate_pdf_file(sample_pdf_path)
    assert ok, message


def test_validate_pdf_rejects_non_pdf(tmp_path):
    path = tmp_path / "fake.pdf"
    path.write_bytes(b"hello world, definitely not a PDF")
    ok, _ = validate_pdf_file(path)
    assert not ok


def test_validate_png(tmp_path, valid_png_bytes):
    path = tmp_path / "img.png"
    path.write_bytes(valid_png_bytes)
    ok, _ = validate_image_file(path)
    assert ok


def test_validate_image_rejects_unknown(tmp_path):
    path = tmp_path / "img.bmp"
    path.write_bytes(b"BM\x00\x00")
    ok, _ = validate_image_file(path)
    assert not ok


def test_parse_page_range_basic():
    assert parse_page_range("1-3,5,8-10", total_pages=10) == [1, 2, 3, 5, 8, 9, 10]


def test_parse_page_range_rejects_out_of_bounds():
    import pytest
    with pytest.raises(ValueError):
        parse_page_range("1-3", total_pages=2)


def test_parse_page_range_rejects_invalid_syntax():
    import pytest
    with pytest.raises(ValueError):
        parse_page_range("a-b", total_pages=5)


def test_parse_page_range_rejects_start_gt_end():
    import pytest
    with pytest.raises(ValueError):
        parse_page_range("5-2", total_pages=10)