import os
import re
import unicodedata

try:
    # Prefer proper transliteration for Cyrillic and other scripts
    from unidecode import unidecode  # type: ignore
except Exception:  # pragma: no cover - fallback when dependency missing
    unidecode = None  # type: ignore


_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _to_ascii(text: str) -> str:
    """Best-effort transliteration to ASCII.

    - Uses unidecode if available
    - Falls back to NFKD + ASCII ignore
    """
    if not text:
        return ""
    if unidecode is not None:
        try:
            return unidecode(text)
        except Exception:
            pass
    # Fallback: strip diacritics and drop non-ascii
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def make_safe_filename(original_name: str, max_length: int = 150) -> str:
    """Create a cross-platform safe ASCII filename.

    - Transliterates to ASCII
    - Replaces spaces with underscores
    - Removes unsafe characters (keeps letters, digits, dot, dash, underscore)
    - Preserves (sanitized) extension
    - Truncates to max_length
    """
    if not original_name:
        return "file"

    # Split extension
    base, ext = os.path.splitext(original_name)

    # Normalize extension: keep only first 10 chars, ascii-only, lowercase
    ext_ascii = _to_ascii(ext).lower()
    # Ensure extension starts with '.' if present
    if ext_ascii and not ext_ascii.startswith('.'):
        ext_ascii = f'.{ext_ascii[:10]}'
    # Limit extension length (just in case of weird inputs)
    if ext_ascii and len(ext_ascii) > 10:
        ext_ascii = ext_ascii[:10]

    # Transliterate and sanitize base
    base_ascii = _to_ascii(base)
    # Replace spaces and consecutive unsafe chars with single underscore
    base_ascii = base_ascii.replace(' ', '_')
    base_ascii = _SAFE_CHARS_RE.sub('_', base_ascii)
    base_ascii = re.sub(r'_+', '_', base_ascii).strip('._-')

    if not base_ascii:
        base_ascii = 'file'

    # Truncate to max length accounting for extension
    remaining = max(1, max_length - len(ext_ascii))
    base_ascii = base_ascii[:remaining]

    safe_name = f"{base_ascii}{ext_ascii}"
    # Final guard: avoid empty
    return safe_name or "file"
