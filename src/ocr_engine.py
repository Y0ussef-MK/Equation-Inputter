from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def validate_image_path(image_path: str) -> str:
    """Return a normalized, valid image path or raise a clear error."""
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"The file '{image_path}' does not exist.")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Please upload a .png, .jpg, or .jpeg image."
        )
    return str(path)


def _sanitize_plain_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", text)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def _sanitize_formula_text(raw: str) -> str:
    formula = str(raw or "").strip()
    formula = formula.replace("\u00a0", " ")
    formula = formula.replace("\\begin{matrix}", "").replace("\\end{matrix}", "")
    formula = formula.replace("\\left", "").replace("\\right", "")
    formula = formula.replace("\\cdot", " ")
    formula = formula.replace("\\text", "")
    formula = formula.replace("\\;", " ")
    formula = formula.replace("\\,", " ")
    formula = re.sub(r"\{\s*", "{", formula)
    formula = re.sub(r"\s*\}", "}", formula)
    formula = re.sub(r"\s+", " ", formula)
    formula = re.sub(r"\s*([=+\-*/^_(){}])\s*", r"\1", formula)
    formula = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", formula)
    formula = re.sub(r"(?<=\d)\s+(?=\d)", "", formula)
    formula = formula.replace(" . ", ".")
    formula = formula.replace(" 0 0 ", "00")
    formula = formula.replace(" 00 ", "00")
    formula = formula.replace(" 0 ", "0")
    formula = formula.replace("\n", " ")
    formula = formula.strip()
    if not formula:
        return ""
    if formula.startswith("$") and formula.endswith("$"):
        formula = formula[1:-1].strip()
    return formula


def _safe_extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    if isinstance(value, (list, tuple, set)):
        parts: list[str] = []
        for item in value:
            text = _safe_extract_text(item)
            if text and text not in parts:
                parts.append(text)
        return "\n".join(parts)
    if isinstance(value, dict):
        for key in ("text", "content", "result", "value", "latex", "ocr_text", "formula"):
            if key in value and value[key] is not None:
                extracted = _safe_extract_text(value[key])
                if extracted:
                    return extracted
        collected: list[str] = []
        for item in value.values():
            text = _safe_extract_text(item)
            if text and text not in collected:
                collected.append(text)
        return "\n".join(collected)
    if hasattr(value, "elements"):
        elements = getattr(value, "elements")
        if elements:
            result: list[str] = []
            for element in elements:
                text = _safe_extract_text(element)
                if text and text not in result:
                    result.append(text)
            return "\n\n".join(result)
    if hasattr(value, "text"):
        text = _safe_extract_text(getattr(value, "text"))
        if text:
            return text
    if hasattr(value, "content"):
        text = _safe_extract_text(getattr(value, "content"))
        if text:
            return text
    return str(value)


def _extract_page_contents(page_result: Any) -> list[str]:
    if page_result is None:
        return []

    extracted: list[str] = []

    if hasattr(page_result, "elements"):
        for element in getattr(page_result, "elements"):
            element_type = getattr(element, "type", "").upper()
            raw_text = getattr(element, "text", "")
            if not raw_text and hasattr(element, "meta"):
                meta = getattr(element, "meta")
                if isinstance(meta, list) and meta:
                    raw_text = getattr(meta[0], "text", "")
                elif isinstance(meta, dict):
                    raw_text = meta.get("text", "")
            if not raw_text:
                continue
            if element_type == "FORMULA":
                formula = _sanitize_formula_text(raw_text)
                if formula:
                    if "\\" in formula or "=" in formula or re.search(r"[A-Za-z]_[A-Za-z]|[A-Za-z]\^\{|\\frac|\\sqrt|\\sum|\\int", formula):
                        extracted.append(f"$$\n{formula}\n$$")
                    else:
                        extracted.append(f"${formula}$")
            elif element_type == "TEXT":
                cleaned = _sanitize_plain_text(raw_text)
                if cleaned:
                    extracted.append(cleaned)
            else:
                cleaned = _sanitize_plain_text(raw_text)
                if cleaned:
                    extracted.append(cleaned)
        return extracted

    if isinstance(page_result, (list, tuple, set)):
        for item in page_result:
            extracted.extend(_extract_page_contents(item))
        return extracted

    if isinstance(page_result, dict):
        for value in page_result.values():
            extracted.extend(_extract_page_contents(value))
        return extracted

    text = _sanitize_plain_text(_safe_extract_text(page_result))
    if text:
        extracted.append(text)
    return extracted


def _looks_like_equation(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if cleaned.startswith(("$", "$$", "\\begin")):
        return True
    if re.search(r"\\(frac|sum|int|sqrt|alpha|beta|gamma|theta|pi)|[A-Za-z]\^\{|[A-Za-z]_\{|[A-Za-z]_[0-9]|[=<>]", cleaned):
        return True
    return False


def _format_output_blocks(text: str) -> str:
    blocks: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if _looks_like_equation(line):
            if "\\" in line or "=" in line or line.count("$") >= 2:
                if not line.startswith("$$"):
                    line = f"$$\n{line}\n$$"
            else:
                if not line.startswith("$"):
                    line = f"${line}$"
        blocks.append(line)
    return "\n\n".join(blocks)


def preprocess_image_for_ocr(image_path: str) -> str:
    """Downsize heavy images to reduce OCR latency while preserving useful detail."""
    with Image.open(image_path) as image:
        rgb_image = ImageOps.exif_transpose(image).convert("RGB")
        max_side = 1600
        width, height = rgb_image.size
        scale = min(1.0, max_side / max(width, height))
        if scale < 1.0:
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            rgb_image = rgb_image.resize(new_size, Image.Resampling.LANCZOS)

        temp_fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(temp_fd)
        rgb_image.save(temp_path, format="PNG")
        return temp_path


def extract_math_ocr(image_path: str) -> str:
    """OCR an image and return cleaned plain text with formulas wrapped as LaTeX."""
    validated_path = validate_image_path(image_path)

    try:
        from pix2text import Pix2Text  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The OCR dependency 'pix2text' is not installed. Install the dependencies from requirements.txt."
        ) from exc

    preprocessed_path = preprocess_image_for_ocr(validated_path)
    try:
        try:
            engine = Pix2Text(resized_shape=768)
        except TypeError:
            try:
                engine = Pix2Text()
            except TypeError:
                engine = None

        result: Any = None
        if engine is not None:
            candidate_calls = [
                lambda: engine(preprocessed_path),
                lambda: engine.recognize(preprocessed_path),
                lambda: engine.run(preprocessed_path),
                lambda: engine.ocr(preprocessed_path),
                lambda: engine.process(preprocessed_path),
            ]
            last_error: Exception | None = None
            for call in candidate_calls:
                try:
                    result = call()
                    break
                except (AttributeError, TypeError, ValueError, NotImplementedError) as exc:
                    last_error = exc
                    continue
                except Exception as exc:  # pragma: no cover - safety fallback
                    last_error = exc
                    break
        if result is None:
            raise RuntimeError(
                "The OCR engine could not process the image. Please try a clearer image or a different file."
            )

        chunks = _extract_page_contents(result)
        if not chunks:
            fallback = _safe_extract_text(result)
            chunks = [fallback] if fallback else []

        text = "\n\n".join(part for part in chunks if part)
        text = _format_output_blocks(text)
        if not text.strip():
            raise RuntimeError("No text could be extracted from the selected image.")
        return text.strip()
    finally:
        try:
            os.remove(preprocessed_path)
        except OSError:
            pass
