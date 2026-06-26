"""DeepSeek OCR parser utilities."""
from __future__ import annotations

import base64
import logging
import mimetypes
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import fitz


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _default_deepseek_ocr_config_path() -> Path:
    """Path to optional DeepSeek-OCR YAML overrides (config/deepseek_ocr_ollama.yaml)."""
    return _project_root() / "config" / "deepseek_ocr_ollama.yaml"


# Default prompt for DeepSeek-OCR. Model expects plain prompt; we ask for Markdown.
# See: https://github.com/deepseek-ai/DeepSeek-OCR (vLLM uses "<image>\nFree OCR." style).
_DEEPSEEK_OCR_DEFAULT_PROMPT = (
    "Recognize the text in the image and output in Markdown format. "
    "Preserve the original layout (headings, paragraphs, tables, formulas). "
    "Do not fabricate content that does not exist in the image."
)

# Regex to strip DeepSeek-OCR ref/det blocks: <|ref|>...<|/ref|><|det|>...<|/det|>
# See: run_dpsk_ocr_pdf.py / run_dpsk_ocr_image.py (re_match and replacement).
_DEEPSEEK_OCR_REF_DET_PATTERN = re.compile(
    r"<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>",
    re.DOTALL,
)


def _deepseek_ocr_clean_output(text: str) -> str:
    """
    Post-process DeepSeek-OCR model output: remove ref/det blocks and LaTeX substitutions.

    The vLLM pipeline replaces image refs with markdown image links and strips other refs;
    we strip all ref/det blocks so the result is clean markdown (no embedded bbox metadata).
    See: https://github.com/deepseek-ai/DeepSeek-OCR (run_dpsk_ocr_pdf.py, run_dpsk_ocr_image.py).
    """
    if not text:
        return text
    out = _DEEPSEEK_OCR_REF_DET_PATTERN.sub("", text)
    out = out.replace("\\coloneqq", ":=").replace("\\eqqcolon", "=:")
    out = re.sub(r"\n\n\n+", "\n\n", out)
    return out.strip()


def _mime_from_extension(ext: str) -> str:
    e = (ext or "").strip().lower()
    if not e:
        return "image/png"
    if not e.startswith("."):
        e = f".{e}"
    mime, _ = mimetypes.guess_type(f"file{e}")
    return mime or "image/png"


def _mime_for_path(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def _load_deepseek_ocr_config(config_path: str | Path | None) -> dict[str, Any]:
    """Load optional overrides; routing defaults to llm_config use case `ocr_deepseek`."""
    defaults: dict[str, Any] = {"use_case": "ocr_deepseek", "model": None, "request_timeout": None}
    if not config_path:
        return defaults
    path = Path(config_path)
    if not path.exists():
        return defaults
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        ocr = (data.get("pipeline") or {}).get("ocr_api") or (data.get("ocr_api") or {})
        if ocr.get("use_case") is not None:
            defaults["use_case"] = str(ocr["use_case"]).strip() or "ocr_deepseek"
        if ocr.get("model") is not None:
            defaults["model"] = str(ocr["model"])
        if ocr.get("request_timeout") is not None:
            defaults["request_timeout"] = int(ocr["request_timeout"])
    except Exception:
        pass
    return defaults


def _deepseek_ocr_llm_service(
    images_b64: list[str],
    prompt: str,
    *,
    use_case: str,
    model: str | None,
    mime_type: str,
    request_timeout: int | None,
) -> str:
    from doc_processing.llm_runtime import HttpLLMRuntime
    from doc_processing.llm_runtime.vision_messages import build_vision_user_messages

    llm = HttpLLMRuntime()
    messages = build_vision_user_messages(prompt, images_b64, mime_type=mime_type)
    t = float(request_timeout) if request_timeout is not None else None
    try:
        return llm.complete_with_fallback(
            messages,
            use_case=use_case,
            model=model,
            timeout_seconds=t,
        )
    except Exception as e:
        logging.getLogger(__name__).warning(
            "DeepSeek-OCR llm-service request failed: %s (use_case=%s)",
            e,
            use_case,
        )
        return ""


def ocr_to_markdown_deepseek_image(
    source: str | Path | bytes,
    file_extension: str | None = None,
    prompt: str | None = None,
    config_path: str | Path | None = None,
    model: str | None = None,
    request_timeout: int | None = None,
    clean_output: bool = True,
) -> str:
    """
    Run DeepSeek-OCR on a single image and return markdown via llm-service.

    Mirrors the vLLM image flow in run_dpsk_ocr_image.py: one image -> one completion
    -> optional post-process (strip ref/det blocks). Contract: llm_service_openapi.json.
    """
    path: Path | None = None
    try:
        if isinstance(source, bytes):
            if not file_extension or not file_extension.strip():
                return ""
            ext = file_extension.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            path = Path(tempfile.mkdtemp(prefix="deepseek_ocr_")) / f"input{ext}"
            path.write_bytes(source)
        else:
            path = Path(source)

        if not path.exists():
            return ""

        suffix = path.suffix.lower()
        if suffix not in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"):
            return ""

        cfg_path = config_path or _default_deepseek_ocr_config_path()
        cfg = _load_deepseek_ocr_config(cfg_path if Path(cfg_path).exists() else None)
        if model is not None:
            cfg["model"] = model
        if request_timeout is not None:
            cfg["request_timeout"] = request_timeout

        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        use_prompt = prompt or _DEEPSEEK_OCR_DEFAULT_PROMPT
        mime = _mime_from_extension(file_extension or suffix) if isinstance(source, bytes) else _mime_for_path(path)
        text = _deepseek_ocr_llm_service(
            [b64],
            use_prompt,
            use_case=cfg["use_case"],
            model=cfg["model"],
            mime_type=mime,
            request_timeout=cfg["request_timeout"],
        )
        if not text:
            return ""
        out = _deepseek_ocr_clean_output(text) if clean_output else text
        return (out or "").strip()
    except Exception as e:
        logging.getLogger(__name__).warning("DeepSeek-OCR image failed: %s", e)
        return ""
    finally:
        if path is not None and isinstance(source, bytes) and path.exists():
            path.unlink(missing_ok=True)
            try:
                shutil.rmtree(path.parent, ignore_errors=True)
            except OSError:
                pass


def ocr_to_markdown_deepseek_pdf(
    source: str | Path | bytes,
    file_extension: str | None = None,
    prompt: str | None = None,
    config_path: str | Path | None = None,
    model: str | None = None,
    request_timeout: int | None = None,
    clean_output: bool = True,
) -> str:
    """Run DeepSeek-OCR on a PDF and return markdown (one llm-service call per page)."""
    path: Path | None = None
    image_paths: list[Path] = []

    try:
        if isinstance(source, bytes):
            if not file_extension or not file_extension.strip():
                return ""
            ext = file_extension.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            path = Path(tempfile.mkdtemp(prefix="deepseek_ocr_")) / f"input{ext}"
            path.write_bytes(source)
        else:
            path = Path(source)

        if not path.exists():
            return ""
        if path.suffix.lower() != ".pdf":
            return ""

        cfg_path = config_path or _default_deepseek_ocr_config_path()
        cfg = _load_deepseek_ocr_config(cfg_path if (cfg_path and Path(cfg_path).exists()) else None)
        if model is not None:
            cfg["model"] = model
        if request_timeout is not None:
            cfg["request_timeout"] = request_timeout

        temp_dir = Path(tempfile.mkdtemp(prefix="deepseek_ocr_pdf_"))
        image_paths = _pdf_to_image_paths(path, temp_dir)
        if not image_paths:
            return ""

        use_prompt = prompt or _DEEPSEEK_OCR_DEFAULT_PROMPT
        parts: list[str] = []
        for i, img_path in enumerate(image_paths):
            b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            text = _deepseek_ocr_llm_service(
                [b64],
                use_prompt,
                use_case=cfg["use_case"],
                model=cfg["model"],
                mime_type="image/png",
                request_timeout=cfg["request_timeout"],
            )
            if text:
                cleaned = _deepseek_ocr_clean_output(text) if clean_output else text
                parts.append(cleaned.strip())
            else:
                logging.getLogger(__name__).warning(
                    "DeepSeek-OCR PDF page %s returned empty.", i + 1
                )
        out = "\n\n".join(parts)
        if not out:
            logging.getLogger(__name__).warning(
                "DeepSeek-OCR PDF returned no content. Check llm-service and llm_config use case ocr_deepseek."
            )
        return out.strip()
    except Exception as e:
        logging.getLogger(__name__).warning("DeepSeek-OCR PDF failed: %s", e)
        return ""
    finally:
        if image_paths:
            temp_dir = image_paths[0].parent
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except OSError:
                pass
        if path is not None and isinstance(source, bytes):
            path.unlink(missing_ok=True)
            try:
                shutil.rmtree(path.parent, ignore_errors=True)
            except OSError:
                pass


def _pdf_to_image_paths(pdf_path: Path, temp_dir: Path) -> list[Path]:
    """Render each PDF page to a PNG in temp_dir; return list of image paths."""
    paths: list[Path] = []
    doc = fitz.open(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc[i]
            pix = page.get_pixmap(dpi=150, alpha=False)
            out = temp_dir / f"page_{i:04d}.png"
            pix.save(str(out))
            paths.append(out)
    finally:
        doc.close()
    return paths

