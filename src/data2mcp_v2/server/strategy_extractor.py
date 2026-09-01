"""
Strategy Extractor: automatically extract structured analysis strategies
from PDF, TXT, or raw text using LLM, then persist them to JSON.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default path for persisted extracted strategies
DEFAULT_STRATEGY_STORE = Path("config/extracted_strategies.json")

EXTRACT_SYSTEM_PROMPT = """\
You are an expert at identifying structured analytical methods and frameworks from academic or professional texts.

Your task: read the provided text excerpt and extract ALL distinct analytical strategies, methods, or frameworks described in it.

For each strategy you find, return a JSON object with these fields:
- "key": a short snake_case identifier (e.g. "ace_analysis", "hypothesis_testing")
- "name": the full human-readable name (e.g. "ACE Analysis", "Hypothesis Testing")
- "description": one sentence summarizing what the strategy does (max 20 words)
- "full_text": a 3-6 sentence instruction for an AI agent on HOW to apply this strategy when querying data sources. Write in imperative form ("Query...", "Decompose...", "First..."). Be concrete and actionable.
- "checkpoints": a list of 3-5 strings. Each string describes a concrete intermediate artifact or structural feature that MUST appear in the final answer if this strategy was correctly applied. These are observable anchors used to verify compliance AFTER the agent finishes — NOT descriptions of process steps. Each checkpoint must be a short, verifiable statement about the output content. Good examples: "lists at least 2 competing hypotheses explicitly", "contains a comparison or matrix between alternatives", "states assumptions before drawing conclusions", "decomposes the question into sub-questions (Who/What/When/Where/Why/How)", "identifies at least one piece of disconfirming evidence". Bad examples (too vague): "is thorough", "uses the method correctly".
- "source": the document name or section this was extracted from

Return a JSON array. If no distinct strategies are found in the excerpt, return an empty array [].
Do NOT include any text outside the JSON array.
""".strip()


def _read_pdf(path: str | Path, max_pages: int = 50) -> str:
    """Extract text from PDF using PyMuPDF (text layer only)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF is required: pip install PyMuPDF")

    doc = fitz.open(str(path))
    pages = min(len(doc), max_pages)
    chunks = []
    for i in range(pages):
        text = doc[i].get_text()
        if text.strip():
            chunks.append(f"[Page {i + 1}]\n{text.strip()}")
    doc.close()
    return "\n\n".join(chunks)


def _read_pdf_vision(
    path: str | Path,
    llm_client: Any,
    max_pages: int = 50,
    dpi_scale: float = 2.0,
    batch_size: int = 3,
    vision_model: str = "gpt-4o",
) -> str:
    """
    OCR fallback: render each PDF page as an image and send to the vision LLM
    to transcribe the text. Used when the PDF has no text layer (scanned).
    Uses a dedicated vision model (default: qwen-vl-max).
    """
    import base64
    from openai import OpenAI

    try:
        import fitz
    except ImportError:
        raise ImportError("PyMuPDF is required: pip install PyMuPDF")

    # Build a vision-capable client reusing the same base_url and api_key
    vision_client = OpenAI(
        api_key=llm_client.client.api_key,
        base_url=str(llm_client.model_url),
    )

    doc = fitz.open(str(path))
    total = min(len(doc), max_pages)
    mat = fitz.Matrix(dpi_scale, dpi_scale)

    all_text_parts: list[str] = []

    # Process pages in small batches to avoid huge payloads
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        content: list[dict] = []

        for i in range(batch_start, batch_end):
            pix = doc[i].get_pixmap(matrix=mat)
            img_b64 = base64.b64encode(pix.tobytes("jpeg")).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

        page_range = f"{batch_start + 1}-{batch_end}"
        content.append({
            "type": "text",
            "text": (
                f"These are pages {page_range} of an academic book on structured analytical methods. "
                "Please transcribe ALL text content from these pages completely and accurately. "
                "Preserve chapter titles, section headings, and body text. "
                "Output plain text only, no markdown formatting."
            ),
        })

        try:
            resp = vision_client.chat.completions.create(
                model=vision_model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
            )
            page_text = resp.choices[0].message.content or ""
            if page_text.strip():
                all_text_parts.append(f"[Pages {page_range}]\n{page_text.strip()}")
                logger.info("Vision OCR pages %s: %d chars", page_range, len(page_text))
        except Exception as exc:
            logger.warning("Vision OCR failed for pages %s: %s", page_range, exc)

    doc.close()
    return "\n\n".join(all_text_parts)


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def _split_into_chunks(text: str, chunk_size: int = 3000, overlap: int = 300) -> list[str]:
    """Split long text into overlapping chunks for LLM processing."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def _extract_json_array(text: str) -> list[dict]:
    """Robustly parse a JSON array from LLM output."""
    text = text.strip()
    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except Exception:
        pass
    # Try to find JSON array in text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, list):
                return result
        except Exception:
            pass
    return []


def _deduplicate(specs: list[dict]) -> list[dict]:
    """Remove duplicate strategies by key, keeping the last seen."""
    seen: dict[str, dict] = {}
    for s in specs:
        key = s.get("key", "")
        if key:
            seen[key] = s
    return list(seen.values())


def extract_strategies_from_text(
    text: str,
    source_name: str,
    llm_client: Any,  # ChatModel instance
    chunk_size: int = 3000,
) -> list[dict]:
    """
    Run LLM extraction on the given text (chunked).
    Returns a list of raw strategy dicts.
    """
    chunks = _split_into_chunks(text, chunk_size=chunk_size, overlap=300)
    all_raw: list[dict] = []

    for i, chunk in enumerate(chunks):
        logger.info("Extracting strategies from chunk %d/%d of '%s'", i + 1, len(chunks), source_name)
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Source document: {source_name}\n\n"
                    f"Text excerpt:\n{chunk}\n\n"
                    "Extract all analytical strategies from the text above. Return JSON array only."
                ),
            },
        ]
        try:
            completion = llm_client.chat_with_retry(messages, retry=2)
            content = completion.choices[0].message.content or ""
            items = _extract_json_array(content)
            for item in items:
                item.setdefault("source", source_name)
                # Ensure key is valid snake_case
                raw_key = item.get("key", "")
                if not raw_key:
                    item["key"] = "strategy_" + uuid.uuid4().hex[:6]
                else:
                    item["key"] = re.sub(r"[^a-z0-9_]", "_", raw_key.lower().strip())
            all_raw.extend(items)
        except Exception as exc:
            logger.warning("Chunk %d extraction failed: %s", i + 1, exc)

    return _deduplicate(all_raw)


def extract_strategies_from_file(
    file_path: str | Path,
    llm_client: Any,
    max_pages: int = 50,
    chunk_size: int = 3000,
) -> list[dict]:
    """
    Extract strategies from a PDF or text file.
    Returns list of strategy dicts ready to be saved.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    source_name = path.name
    suffix = path.suffix.lower()

    logger.info("Reading file: %s", path)
    if suffix == ".pdf":
        text = _read_pdf(path, max_pages=max_pages)
        if not text.strip():
            # Scanned PDF: fall back to vision LLM OCR
            logger.info("No text layer found in PDF '%s', switching to vision OCR", source_name)
            text = _read_pdf_vision(path, llm_client, max_pages=max_pages)
    elif suffix in (".txt", ".md", ".rst"):
        text = _read_text(path)
    else:
        text = _read_text(path)

    if not text.strip():
        raise ValueError(f"No readable text found in: {path}")

    logger.info("Extracted %d characters from '%s'", len(text), source_name)
    return extract_strategies_from_text(text, source_name, llm_client, chunk_size=chunk_size)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def load_extracted_strategies(store_path: str | Path = DEFAULT_STRATEGY_STORE) -> list[dict]:
    """Load previously extracted strategies from the JSON store."""
    p = Path(store_path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Failed to load strategy store %s: %s", p, exc)
        return []


def save_extracted_strategies(
    strategies: list[dict],
    store_path: str | Path = DEFAULT_STRATEGY_STORE,
    merge: bool = True,
) -> list[dict]:
    """
    Persist extracted strategies to JSON.
    If merge=True, merges with existing strategies (new ones override by key).
    Returns the final merged list.
    """
    p = Path(store_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if merge:
        existing = load_extracted_strategies(p)
        merged = {s["key"]: s for s in existing}
        for s in strategies:
            merged[s["key"]] = s
        final = list(merged.values())
    else:
        final = strategies

    p.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d strategies to %s", len(final), p)
    return final


def delete_extracted_strategy(
    key: str,
    store_path: str | Path = DEFAULT_STRATEGY_STORE,
) -> bool:
    """Remove a strategy by key from the store. Returns True if found and removed."""
    existing = load_extracted_strategies(store_path)
    filtered = [s for s in existing if s.get("key") != key]
    if len(filtered) == len(existing):
        return False
    Path(store_path).write_text(
        json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return True
