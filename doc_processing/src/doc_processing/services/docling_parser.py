"""Docling-based parsers for PDF/XBRL and markdown export helpers."""
from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import shutil
import tempfile

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TableStructureOptions,
    VlmPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption, XBRLFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

from doc_processing.debug_trace import (
    debug_print,
    is_debug_enabled,
    resolve_docling_debug_dir,
    write_debug_json,
    write_debug_text,
)
from doc_processing.llm_runtime.docling_vlm import (
    build_picture_description_options,
    build_vlm_convert_options,
)

logger = logging.getLogger(__name__)


def _log_docling_exception(context: str, exc: BaseException, **details: Any) -> None:
    """Log full traceback when DEBUG=true; otherwise a short warning."""
    detail_str = ", ".join(f"{k}={v!r}" for k, v in details.items())
    prefix = f"docling_parser {context}"
    if detail_str:
        prefix = f"{prefix} ({detail_str})"
    if is_debug_enabled():
        debug_print(f"{prefix}: {exc!r}")
        debug_print(traceback.format_exc())
    else:
        logger.warning("%s: %s", prefix, exc)


def _debug_save_conv_result(
    function_name: str,
    conv_result: Any,
    *,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """Write Docling conversion output to ``data/temp/debug/...`` when DEBUG is on."""
    run_dir = resolve_docling_debug_dir(function_name)
    if run_dir is None:
        return

    meta: dict[str, Any] = {"function": function_name, "success": conv_result is not None}
    if extra_meta:
        meta.update(extra_meta)

    if conv_result is None:
        write_debug_json(run_dir, "result_meta.json", {**meta, "status": "failed"})
        debug_print(f"{function_name}: conversion returned None")
        return

    doc = getattr(conv_result, "document", None)
    if doc is None:
        write_debug_json(run_dir, "result_meta.json", {**meta, "status": "no_document"})
        debug_print(f"{function_name}: conversion result has no document")
        return

    markdown = ""
    try:
        markdown = (doc.export_to_markdown() or "").strip()
        write_debug_text(run_dir, "output.md", markdown)
    except Exception as e:
        write_debug_text(run_dir, "output.md", f"# export_to_markdown failed\n\n{e!s}")
        meta["export_error"] = str(e)

    write_debug_json(
        run_dir,
        "result_meta.json",
        {
            **meta,
            "status": "ok",
            "markdown_chars": len(markdown),
        },
    )
    debug_print(f"{function_name}: wrote output.md ({len(markdown)} chars) -> {run_dir}")


def _debug_save_markdown_output(function_name: str, markdown: str) -> None:
    """Write string markdown result (e.g. XBRL) under the docling debug folder."""
    run_dir = resolve_docling_debug_dir(function_name)
    if run_dir is None:
        return
    text = (markdown or "").strip()
    write_debug_text(run_dir, "output.md", text)
    write_debug_json(
        run_dir,
        "result_meta.json",
        {
            "function": function_name,
            "status": "ok" if text else "empty",
            "markdown_chars": len(text),
        },
    )
    debug_print(f"{function_name}: wrote output.md ({len(text)} chars) -> {run_dir}")


def _configure_picture_options(pipeline_options: Any) -> None:
    """Enable picture handling options when available on a pipeline options object."""
    if hasattr(pipeline_options, "generate_picture_images"):
        pipeline_options.generate_picture_images = True
    if hasattr(pipeline_options, "do_picture_description"):
        pipeline_options.do_picture_description = True
    if hasattr(pipeline_options, "do_picture_classification"):
        pipeline_options.do_picture_classification = True
    pdesc = getattr(pipeline_options, "picture_description_options", None)
    if pdesc is not None and hasattr(pdesc, "picture_area_threshold"):
        pdesc.picture_area_threshold = 0.05


def _configure_picture_description_vlm(pipeline_options: Any) -> None:
    """Configure Docling picture-description via Ollama (``VlmEngineType.API_OLLAMA``)."""
    try:
        pipeline_options.enable_remote_services = True
    except Exception as e:
        _log_docling_exception("enable_remote_services", e)

    try:
        pipeline_options.picture_description_options = build_picture_description_options(
            "docling_picture_description",
            prompt="Describe the image in three sentences. Be concise and accurate.",
        )
    except Exception as e:
        _log_docling_exception("picture_description_options", e)


# Perceptual-hash match threshold (phash and dhash; min distance must be <= this).
_DEFAULT_MAX_HAMMING_DISTANCE = 8

# Letterhead/footer logos: keep the first small graphic only (see dedupe stats).
_DECOR_MAX_LONG_EDGE = 130
_DECOR_MAX_SHORT_EDGE = 45

_HASH_NORMALIZE_SIZE = 64


@dataclass(frozen=True)
class PictureFingerprint:
    """Dual perceptual hash for scale-tolerant duplicate detection."""

    phash: Any
    dhash: Any


@dataclass
class _PictureRecord:
    element: Any
    fingerprint: PictureFingerprint | None
    width: int
    height: int


def _normalize_image_for_hash(img: Any) -> Any:
    """Resize before hashing so the same logo at different resolutions still matches."""
    from PIL import Image

    rgb = img.convert("RGB")
    return rgb.resize((_HASH_NORMALIZE_SIZE, _HASH_NORMALIZE_SIZE), Image.Resampling.LANCZOS)


def _picture_fingerprint(img: Any) -> PictureFingerprint:
    import imagehash  # type: ignore

    normalized = _normalize_image_for_hash(img)
    return PictureFingerprint(
        phash=imagehash.phash(normalized),
        dhash=imagehash.dhash(normalized),
    )


def fingerprint_distance(a: PictureFingerprint, b: PictureFingerprint) -> int:
    """Hamming distance; use the better of phash and dhash."""
    try:
        return min(int(a.phash - b.phash), int(a.dhash - b.dhash))
    except Exception:
        return 999999


def compare_images(
    hashes: list[Any],
    *,
    max_hamming_distance: int = _DEFAULT_MAX_HAMMING_DISTANCE,
) -> set[int]:
    """Identify visually similar images by comparing perceptual hashes.

    Keeps the first occurrence of each unique image and returns indices to remove.
    """
    keep_indices: list[int] = []
    remove_indices: set[int] = set()

    for i, h in enumerate(hashes):
        is_duplicate = False
        for j in keep_indices:
            try:
                dist = int(h - hashes[j])
            except Exception:
                dist = 999999
            if dist <= max_hamming_distance:
                is_duplicate = True
                break
        if is_duplicate:
            remove_indices.add(i)
        else:
            keep_indices.append(i)

    return remove_indices


def compare_picture_fingerprints(
    fingerprints: list[PictureFingerprint],
    *,
    max_hamming_distance: int = _DEFAULT_MAX_HAMMING_DISTANCE,
) -> set[int]:
    """Like ``compare_images`` but uses phash + dhash (more robust across sizes/compression)."""
    keep_indices: list[int] = []
    remove_indices: set[int] = set()

    for i, fp in enumerate(fingerprints):
        is_duplicate = False
        for j in keep_indices:
            if fingerprint_distance(fp, fingerprints[j]) <= max_hamming_distance:
                is_duplicate = True
                break
        if is_duplicate:
            remove_indices.add(i)
        else:
            keep_indices.append(i)

    return remove_indices


def _is_decorative_picture_size(width: int, height: int) -> bool:
    """Small header/footer graphics (logos, rule lines) — not full charts or signatures."""
    long_edge = max(width, height)
    short_edge = min(width, height)
    return long_edge <= _DECOR_MAX_LONG_EDGE and short_edge <= _DECOR_MAX_SHORT_EDGE


def _decor_collapse_indices(records: list[_PictureRecord], *, already_removed: set[int]) -> set[int]:
    """After exact duplicates are removed, keep only the first small letterhead-style image."""
    extra: set[int] = set()
    kept_decor = False
    for i, rec in enumerate(records):
        if i in already_removed or rec.fingerprint is None:
            continue
        if _is_decorative_picture_size(rec.width, rec.height):
            if kept_decor:
                extra.add(i)
            else:
                kept_decor = True
    return extra


def _log_picture_dedupe_stats(stats: dict[str, Any]) -> None:
    if stats.get("skipped"):
        logger.info("picture dedupe skipped: %s", stats["skipped"])
        debug_print("picture dedupe skipped:", stats["skipped"])
        return

    summary = (
        f"picture dedupe: seen={stats.get('pictures_seen', 0)} "
        f"hashable={stats.get('pictures_hashable', 0)} "
        f"no_image={stats.get('pictures_no_image', 0)} "
        f"hash_failed={stats.get('pictures_hash_failed', 0)} "
        f"duplicate_removed={stats.get('duplicate_removed', 0)} "
        f"decor_collapsed={stats.get('decor_collapsed', 0)} "
        f"total_removed={stats.get('total_removed', 0)} "
        f"kept={stats.get('pictures_kept', 0)} "
        f"delete_ok={stats.get('delete_ok', True)}"
    )
    logger.info(summary)
    debug_print(summary)
    groups = stats.get("hash_groups")
    if groups:
        debug_print("picture dedupe hash groups (kept_count, removed_count):", groups)


def dedupe_common_pictures_in_doc(
    doc: Any,
    *,
    max_hamming_distance: int = _DEFAULT_MAX_HAMMING_DISTANCE,
    collapse_decor: bool = True,
) -> dict[str, Any]:
    """Remove repeated pictures (logos) from a DoclingDocument, preserving order.

  Pass 1: perceptual-hash duplicates (same logo at different sizes).
  Pass 2 (optional): keep only the first small letterhead/footer graphic.

  Returns stats for logging/debug (also written when DEBUG is enabled).
    """
    stats: dict[str, Any] = {
        "pictures_seen": 0,
        "pictures_hashable": 0,
        "pictures_no_image": 0,
        "pictures_hash_failed": 0,
        "duplicate_removed": 0,
        "decor_collapsed": 0,
        "total_removed": 0,
        "pictures_kept": 0,
        "delete_ok": True,
    }

    try:
        import imagehash  # type: ignore  # noqa: F401
    except ImportError:
        stats["skipped"] = "imagehash not installed"
        _log_picture_dedupe_stats(stats)
        return stats

    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        stats["skipped"] = "Pillow not installed"
        _log_picture_dedupe_stats(stats)
        return stats

    records: list[_PictureRecord] = []

    for element, _level in doc.iterate_items(traverse_pictures=True):
        name = element.__class__.__name__.lower()
        if "picture" not in name:
            continue
        stats["pictures_seen"] += 1
        try:
            img = element.get_image(doc)
            if img is None:
                stats["pictures_no_image"] += 1
                records.append(_PictureRecord(element=element, fingerprint=None, width=0, height=0))
                continue
            width, height = img.size
            fp = _picture_fingerprint(img)
            stats["pictures_hashable"] += 1
            records.append(
                _PictureRecord(element=element, fingerprint=fp, width=width, height=height)
            )
        except Exception as e:
            stats["pictures_hash_failed"] += 1
            records.append(_PictureRecord(element=element, fingerprint=None, width=0, height=0))
            debug_print(f"picture dedupe: hash failed for {name}: {e!r}")

    hashable = [r.fingerprint for r in records if r.fingerprint is not None]
    if not hashable:
        stats["pictures_kept"] = stats["pictures_seen"]
        _log_picture_dedupe_stats(stats)
        return stats

    hashable_indices = [i for i, r in enumerate(records) if r.fingerprint is not None]
    fps = [records[i].fingerprint for i in hashable_indices]
    assert all(fp is not None for fp in fps)

    dup_local = compare_picture_fingerprints(
        fps,  # type: ignore[arg-type]
        max_hamming_distance=max_hamming_distance,
    )
    remove_indices: set[int] = {hashable_indices[i] for i in dup_local}
    stats["duplicate_removed"] = len(remove_indices)

    # Hash group stats for DEBUG (phash -> counts)
    group_kept: dict[str, int] = {}
    group_removed: dict[str, int] = {}
    keep_local: list[int] = []
    for i, fp in enumerate(fps):
        key = str(fp.phash)
        if i in dup_local:
            group_removed[key] = group_removed.get(key, 0) + 1
        else:
            keep_local.append(i)
            group_kept[key] = group_kept.get(key, 0) + 1
    stats["hash_groups"] = {
        k: {"kept": group_kept.get(k, 0), "removed": group_removed.get(k, 0)}
        for k in set(group_kept) | set(group_removed)
    }

    if collapse_decor:
        decor_extra = _decor_collapse_indices(records, already_removed=remove_indices)
        stats["decor_collapsed"] = len(decor_extra)
        remove_indices |= decor_extra

    stats["total_removed"] = len(remove_indices)
    stats["pictures_kept"] = stats["pictures_seen"] - stats["total_removed"]

    if not remove_indices:
        _log_picture_dedupe_stats(stats)
        return stats

    node_items_to_delete = [records[i].element for i in sorted(remove_indices)]
    try:
        doc.delete_items(node_items=node_items_to_delete)
    except TypeError:
        try:
            doc.delete_items(node_items_to_delete)
        except Exception as e:
            stats["delete_ok"] = False
            _log_docling_exception("picture dedupe delete_items", e)
    except Exception as e:
        stats["delete_ok"] = False
        _log_docling_exception("picture dedupe delete_items", e)

    _log_picture_dedupe_stats(stats)
    return stats


def _dedupe_common_pictures_in_doc(doc: Any, **kwargs: Any) -> dict[str, Any]:
    """Backward-compatible alias used by parsers."""
    return dedupe_common_pictures_in_doc(doc, **kwargs)


def _prepare_local_source_path(
    source: str | Path | bytes,
    *,
    expected_exts: tuple[str, ...],
    file_extension: str | None = None,
) -> tuple[Path | None, bool]:
    """Return (path, should_cleanup) with validation for local inputs."""
    if isinstance(source, bytes):
        if not file_extension:
            return None, False
        ext = file_extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext not in expected_exts:
            return None, False
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(source)
            return Path(f.name), True

    path = Path(source)
    if not path.exists() or path.suffix.lower() not in expected_exts:
        return None, False
    return path, False


def parse_pdf_using_docling(
    source: str | Path | bytes,
    file_extension: str | None = None,
    backend: Literal["easyocr", "vlm"] = "easyocr",
    embed_image: bool = True,
) -> Any:
    """
    Parse a PDF with Docling and return the Docling conversion result object.

    This function performs the heavy lifting for PDF parsing and pipeline setup.
    Callers can then serialize the returned `conv_result.document` as needed.

    Returns:
        Docling conversion result on success; None on failure/invalid input.
    """
    path: Path | None = None
    try:
        if isinstance(source, bytes):
            if not file_extension or ".pdf" not in file_extension.strip().lower():
                _debug_save_conv_result(
                    "parse_pdf_using_docling",
                    None,
                    extra_meta={"backend": backend, "status": "invalid_bytes_input"},
                )
                return None
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(source)
                path = Path(f.name)
        else:
            path = Path(source)

        if not path or not path.exists() or path.suffix.lower() != ".pdf":
            _debug_save_conv_result("parse_pdf_using_docling", None, extra_meta={"backend": backend})
            return None

        if backend == "easyocr":
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.ocr_options = EasyOcrOptions()
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options = TableStructureOptions(
                do_cell_matching=True
            )
            if embed_image:
                _configure_picture_options(pipeline_options)
                _configure_picture_description_vlm(pipeline_options)
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
        else:
            vlm_options = build_vlm_convert_options(
                "granite_docling",
                "docling_pdf_vlm",
            )
            pipeline_options = VlmPipelineOptions(
                vlm_options=vlm_options,
                enable_remote_services=True,
            )
            if embed_image:
                _configure_picture_options(pipeline_options)
                _configure_picture_description_vlm(pipeline_options)
            doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                        pipeline_cls=VlmPipeline,
                    )
                }
            )

        conv_result = doc_converter.convert(str(path))
        dedupe_stats: dict[str, Any] = {}
        try:
            doc = getattr(conv_result, "document", None)
            if doc is not None:
                dedupe_stats = _dedupe_common_pictures_in_doc(doc)
        except Exception as e:
            _log_docling_exception("dedupe_common_pictures", e)
        _debug_save_conv_result(
            "parse_pdf_using_docling",
            conv_result,
            extra_meta={
                "backend": backend,
                "embed_image": embed_image,
                "picture_dedupe": dedupe_stats,
            },
        )
        return conv_result
    except Exception as e:
        _log_docling_exception(
            "parse_pdf_using_docling",
            e,
            backend=backend,
            embed_image=embed_image,
        )
        _debug_save_conv_result(
            "parse_pdf_using_docling",
            None,
            extra_meta={"backend": backend, "embed_image": embed_image, "status": "exception"},
        )
        return None
    finally:
        if isinstance(source, bytes) and path is not None:
            path.unlink(missing_ok=True)


def parse_markdown_using_docling(
    source: str | Path | bytes,
    file_extension: str | None = None,
    embed_image: bool = True,
) -> Any:
    """
    Parse a Markdown document with Docling and return the conversion result object.

    Markdown is already structured, so no VLM branch is used.
    """
    path, should_cleanup = _prepare_local_source_path(
        source,
        expected_exts=(".md", ".markdown"),
        file_extension=file_extension,
    )
    if path is None:
        _debug_save_conv_result(
            "parse_markdown_using_docling",
            None,
            extra_meta={"embed_image": embed_image, "status": "invalid_input"},
        )
        return None

    try:
        converter = DocumentConverter(allowed_formats=[InputFormat.MD])
        if embed_image:
            option = converter.format_to_options.get(InputFormat.MD)
            if option is not None:
                pipeline_options = getattr(option, "pipeline_options", None)
                if pipeline_options is not None:
                    _configure_picture_options(pipeline_options)
                    _configure_picture_description_vlm(pipeline_options)

        conv_result = converter.convert(str(path))
        dedupe_stats: dict[str, Any] = {}
        try:
            doc = getattr(conv_result, "document", None)
            if doc is not None:
                dedupe_stats = _dedupe_common_pictures_in_doc(doc)
        except Exception as e:
            _log_docling_exception("dedupe_common_pictures", e)
        _debug_save_conv_result(
            "parse_markdown_using_docling",
            conv_result,
            extra_meta={"embed_image": embed_image, "picture_dedupe": dedupe_stats},
        )
        return conv_result
    except Exception:
        _debug_save_conv_result(
            "parse_markdown_using_docling",
            None,
            extra_meta={"embed_image": embed_image, "status": "exception"},
        )
        return None
    finally:
        if should_cleanup and path is not None:
            path.unlink(missing_ok=True)


def parse_html_using_docling(
    source: str | Path | bytes,
    file_extension: str | None = None,
    embed_image: bool = True,
) -> Any:
    """
    Parse an HTML/XHTML document with Docling and return the conversion result object.

    HTML is already structured, so no VLM branch is used.
    """
    path, should_cleanup = _prepare_local_source_path(
        source,
        expected_exts=(".html", ".htm", ".xhtml"),
        file_extension=file_extension,
    )
    if path is None:
        _debug_save_conv_result(
            "parse_html_using_docling",
            None,
            extra_meta={"embed_image": embed_image, "status": "invalid_input"},
        )
        return None

    try:
        converter = DocumentConverter(allowed_formats=[InputFormat.HTML, InputFormat.XHTML])
        if embed_image:
            for fmt in (InputFormat.HTML, InputFormat.XHTML):
                option = converter.format_to_options.get(fmt)
                if option is None:
                    continue
                pipeline_options = getattr(option, "pipeline_options", None)
                if pipeline_options is not None:
                    _configure_picture_options(pipeline_options)
                    _configure_picture_description_vlm(pipeline_options)
        conv_result = converter.convert(str(path))
        dedupe_stats: dict[str, Any] = {}
        try:
            doc = getattr(conv_result, "document", None)
            if doc is not None:
                dedupe_stats = _dedupe_common_pictures_in_doc(doc)
        except Exception as e:
            _log_docling_exception("dedupe_common_pictures", e)
        _debug_save_conv_result(
            "parse_html_using_docling",
            conv_result,
            extra_meta={"embed_image": embed_image, "picture_dedupe": dedupe_stats},
        )
        return conv_result
    except Exception:
        _debug_save_conv_result(
            "parse_html_using_docling",
            None,
            extra_meta={"embed_image": embed_image, "status": "exception"},
        )
        return None
    finally:
        if should_cleanup and path is not None:
            path.unlink(missing_ok=True)


def pdf_to_markdown_docling(
    source: str | Path | bytes,
    file_extension: str | None = None,
    backend: Literal["easyocr", "vlm"] = "easyocr",
    merge_tables: bool = False,
    embed_image: bool = True,
) -> tuple[str, list[Any]]:
    """
    Convert a PDF to markdown using Docling.

    Signature intentionally kept stable for existing callers.
    """
    conv_result = parse_pdf_using_docling(
        source=source,
        file_extension=file_extension,
        backend=backend,
        embed_image=embed_image,
    )
    if conv_result is None:
        return ("", [])

    try:
        if embed_image:
            from docling_core.types.doc import ImageRefMode

            tmp_md: Path | None = None
            try:
                tmp_md = Path(tempfile.mkdtemp(prefix="docling_md_")) / "doc.md"
                conv_result.document.save_as_markdown(tmp_md, image_mode=ImageRefMode.EMBEDDED)
                markdown = (tmp_md.read_text(encoding="utf-8") or "").strip()
            finally:
                if tmp_md is not None:
                    try:
                        shutil.rmtree(tmp_md.parent, ignore_errors=True)
                    except OSError:
                        pass
        else:
            markdown = (conv_result.document.export_to_markdown() or "").strip()

        if merge_tables:
            from doc_processing.services.pdf_markdown_cleanup import (
                merge_split_tables_and_remove_header_footer,
            )

            markdown = merge_split_tables_and_remove_header_footer(markdown)
        return (markdown, [])
    except Exception:
        return ("", [])


def xbrl_to_markdown(
    source: str | Path | bytes,
    file_extension: str | None = None,
    taxonomy_dir: Path | None = None,
) -> str:
    """Convert an XBRL instance document to markdown using Docling's XBRL backend."""
    from doc_processing.config import get_settings
    from docling.datamodel.backend_options import XBRLBackendOptions

    path: Path | None = None
    if isinstance(source, bytes):
        if not file_extension or all(ext not in file_extension.lower() for ext in (".xml", ".xbrl")):
            _debug_save_markdown_output("xbrl_to_markdown", "")
            return ""
        with tempfile.NamedTemporaryFile(suffix=file_extension or ".xml", delete=False) as f:
            f.write(source)
            path = Path(f.name)
    else:
        path = Path(source)

    if not path or not path.exists():
        _debug_save_markdown_output("xbrl_to_markdown", "")
        return ""
    if path.suffix.lower() not in (".xml", ".xbrl"):
        _debug_save_markdown_output("xbrl_to_markdown", "")
        return ""

    settings = get_settings()
    if taxonomy_dir is None:
        if getattr(settings, "xbrl_taxonomy_dir", None):
            taxonomy_dir = Path(settings.xbrl_taxonomy_dir).expanduser().resolve()
        else:
            taxonomy_dir = Path("data") / "nse"

    try:
        backend_options = XBRLBackendOptions(
            enable_local_fetch=True,
            enable_remote_fetch=True,
            taxonomy=taxonomy_dir,
        )
        converter = DocumentConverter(
            allowed_formats=[InputFormat.XML_XBRL],
            format_options={
                InputFormat.XML_XBRL: XBRLFormatOption(backend_options=backend_options)
            },
        )
        result = converter.convert(str(path))
        doc = result.document
        markdown = (doc.export_to_markdown() or "").strip()
        _debug_save_markdown_output("xbrl_to_markdown", markdown)
        return markdown
    except Exception:
        _debug_save_markdown_output("xbrl_to_markdown", "")
        return ""
    finally:
        if isinstance(source, bytes) and path is not None:
            path.unlink(missing_ok=True)

