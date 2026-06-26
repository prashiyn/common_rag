from __future__ import annotations

import imagehash
from PIL import Image

from doc_processing.services.docling_parser import (
    PictureFingerprint,
    _decor_collapse_indices,
    _is_decorative_picture_size,
    _normalize_image_for_hash,
    _PictureRecord,
    compare_picture_fingerprints,
    fingerprint_distance,
)


def _fp(img: Image.Image) -> PictureFingerprint:
    n = _normalize_image_for_hash(img)
    return PictureFingerprint(phash=imagehash.phash(n), dhash=imagehash.dhash(n))


def test_same_logo_different_sizes_matches() -> None:
    a = Image.new("RGB", (85, 35), color=(200, 50, 50))
    b = Image.new("RGB", (170, 70), color=(200, 50, 50))
    fps = [_fp(a), _fp(b)]
    assert fingerprint_distance(fps[0], fps[1]) <= 8
    assert compare_picture_fingerprints(fps) == {1}


def test_decorative_size_heuristic() -> None:
    assert _is_decorative_picture_size(85, 35) is True
    assert _is_decorative_picture_size(121, 84) is False


def test_decor_collapse_keeps_first_small_graphic_only() -> None:
    records = [
        _PictureRecord(element=0, fingerprint=_fp(Image.new("RGB", (10, 10))), width=85, height=35),
        _PictureRecord(element=1, fingerprint=_fp(Image.new("RGB", (20, 20))), width=112, height=19),
        _PictureRecord(element=2, fingerprint=_fp(Image.new("RGB", (30, 30))), width=121, height=84),
    ]
    extra = _decor_collapse_indices(records, already_removed=set())
    assert extra == {1}
