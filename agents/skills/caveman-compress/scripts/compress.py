#!/usr/bin/env python3
"""
Caveman Memory Compression Orchestrator

Usage:
    python scripts/compress.py <filepath>
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List

OUTER_FENCE_REGEX = re.compile(
    r"\A\s*(`{3,}|~{3,})[^\n]*\n(.*)\n\1\s*\Z", re.DOTALL
)

# Filenames and paths that almost certainly hold secrets or PII. Compressing
# them ships raw bytes to the Anthropic API — a third-party data boundary that
# developers on sensitive codebases cannot cross. detect.py already skips .env
# by extension, but credentials.md / secrets.txt / ~/.aws/credentials would
# slip through the natural-language filter. This is a hard refuse before read.
SENSITIVE_BASENAME_REGEX = re.compile(
    r"(?ix)^("
    r"\.env(\..+)?"
    r"|\.netrc"
    r"|credentials(\..+)?"
    r"|secrets?(\..+)?"
    r"|passwords?(\..+)?"
    r"|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?"
    r"|authorized_keys"
    r"|known_hosts"
    r"|.*\.(pem|key|p12|pfx|crt|cer|jks|keystore|asc|gpg)"
    r")$"
)

SENSITIVE_PATH_COMPONENTS = frozenset({".ssh", ".aws", ".gnupg", ".kube", ".docker"})

SENSITIVE_NAME_TOKENS = (
    "secret", "credential", "password", "passwd",
    "apikey", "accesskey", "token", "privatekey",
)


def is_sensitive_path(filepath: Path) -> bool:
    """Heuristic denylist for files that must never be shipped to a third-party API."""
    name = filepath.name
    if SENSITIVE_BASENAME_REGEX.match(name):
        return True
    lowered_parts = {p.lower() for p in filepath.parts}
    if lowered_parts & SENSITIVE_PATH_COMPONENTS:
        return True
    # Normalize separators so "api-key" and "api_key" both match "apikey".
    lower = re.sub(r"[_\-\s.]", "", name.lower())
    return any(tok in lower for tok in SENSITIVE_NAME_TOKENS)


def strip_llm_wrapper(text: str) -> str:
    """Strip outer ```markdown ... ``` fence when it wraps the entire output."""
    m = OUTER_FENCE_REGEX.match(text)
    if m:
        return m.group(2)
    return text

from .detect import should_compress
from .validate import validate

MAX_RETRIES = 2

PROTECTED_TOKEN_RE = re.compile(r"__CAVEMAN_[A-Z]+_\d+__")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^\)]+\)")
URL_RE = re.compile(r"https?://[^\s)]+")
REDUNDANT_PHRASES = (
    (re.compile(r"\bin order to\b", re.IGNORECASE), "to"),
    (re.compile(r"\bmake sure to\b", re.IGNORECASE), "ensure"),
    (re.compile(r"\bthe reason is because\b", re.IGNORECASE), "because"),
    (re.compile(r"\byou should\b", re.IGNORECASE), ""),
    (re.compile(r"\bremember to\b", re.IGNORECASE), ""),
)
DROP_WORDS_RE = re.compile(
    r"\b(a|an|the|just|really|basically|actually|simply|essentially|generally|"
    r"however|furthermore|additionally)\b",
    re.IGNORECASE,
)
WHITESPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")


def _protect_spans(text: str) -> tuple[str, dict[str, str]]:
    protected: dict[str, str] = {}
    counters = {"LINK": 0, "URL": 0, "CODE": 0}

    def repl(kind: str):
        def _inner(match: re.Match[str]) -> str:
            token = f"__CAVEMAN_{kind}_{counters[kind]}__"
            counters[kind] += 1
            protected[token] = match.group(0)
            return token

        return _inner

    text = MARKDOWN_LINK_RE.sub(repl("LINK"), text)
    text = URL_RE.sub(repl("URL"), text)
    text = INLINE_CODE_RE.sub(repl("CODE"), text)
    return text, protected


def _restore_spans(text: str, protected: dict[str, str]) -> str:
    for token, value in protected.items():
        text = text.replace(token, value)
    return text


def _compress_text_fragment(text: str) -> str:
    if not text.strip():
        return text

    working, protected = _protect_spans(text)
    for pattern, replacement in REDUNDANT_PHRASES:
        working = pattern.sub(replacement, working)

    pieces = re.split(r"(\s+)", working)
    compact: list[str] = []
    for piece in pieces:
        if not piece or piece.isspace():
            compact.append(piece)
            continue
        if PROTECTED_TOKEN_RE.fullmatch(piece):
            compact.append(piece)
            continue
        stripped = DROP_WORDS_RE.sub("", piece)
        stripped = stripped.strip()
        if stripped:
            compact.append(stripped)

    working = "".join(compact)
    working = re.sub(r"\s+", " ", working).strip()
    working = WHITESPACE_BEFORE_PUNCT_RE.sub(r"\1", working)
    working = re.sub(r"\bdo not\b", "don't", working, flags=re.IGNORECASE)
    working = re.sub(r"\bdoes not\b", "doesn't", working, flags=re.IGNORECASE)
    return _restore_spans(working, protected)


def local_compress_markdown(text: str) -> str:
    lines = text.splitlines()
    compressed_lines: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        fence_match = FENCE_OPEN_REGEX.match(line)
        if fence_match:
            current_char = fence_match.group(2)[0]
            current_len = len(fence_match.group(2))
            if not in_fence:
                in_fence = True
                fence_char = current_char
                fence_len = current_len
            elif current_char == fence_char and current_len >= fence_len and fence_match.group(3).strip() == "":
                in_fence = False
                fence_char = ""
                fence_len = 0
            compressed_lines.append(line)
            continue

        if in_fence or not line.strip():
            compressed_lines.append(line)
            continue

        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]

        if stripped.startswith("#"):
            compressed_lines.append(line)
            continue

        marker_match = re.match(r"((?:[-*+]\s+)|(?:\d+\.\s+)|(?:>\s+))", stripped)
        if marker_match:
            marker = marker_match.group(1)
            body = stripped[len(marker) :]
            compressed_lines.append(f"{indent}{marker}{_compress_text_fragment(body)}")
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            compressed_lines.append(line)
            continue

        compressed_lines.append(f"{indent}{_compress_text_fragment(stripped)}")

    result = "\n".join(compressed_lines)
    if text.endswith("\n"):
        result += "\n"
    return result


# ---------- Claude Calls ----------


def call_claude(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=os.environ.get("CAVEMAN_MODEL", "claude-sonnet-4-5"),
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return strip_llm_wrapper(msg.content[0].text.strip())
        except ImportError:
            pass  # anthropic not installed, fall back to CLI
    # Fallback: use claude CLI (handles desktop auth)
    try:
        result = subprocess.run(
            ["claude", "--print"],
            input=prompt,
            text=True,
            capture_output=True,
            check=True,
        )
        return strip_llm_wrapper(result.stdout.strip())
    except FileNotFoundError:
        raise RuntimeError("Claude CLI not found")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Claude call failed:\n{e.stderr}")


def compress_content(original: str) -> str:
    try:
        return call_claude(build_compress_prompt(original))
    except RuntimeError as exc:
        print(f"Claude unavailable ({exc}); using local fallback compressor")
        return local_compress_markdown(original)


def fix_content(original: str, compressed: str, errors: List[str]) -> str:
    try:
        return call_claude(build_fix_prompt(original, compressed, errors))
    except RuntimeError as exc:
        print(f"Claude unavailable during fix ({exc}); retrying with local fallback compressor")
        return local_compress_markdown(original)


def build_compress_prompt(original: str) -> str:
    return f"""
Compress this markdown into caveman format.

STRICT RULES:
- Do NOT modify anything inside ``` code blocks
- Do NOT modify anything inside inline backticks
- Preserve ALL URLs exactly
- Preserve ALL headings exactly
- Preserve file paths and commands
- Return ONLY the compressed markdown body — do NOT wrap the entire output in a ```markdown fence or any other fence. Inner code blocks from the original stay as-is; do not add a new outer fence around the whole file.

Only compress natural language.

TEXT:
{original}
"""


def build_fix_prompt(original: str, compressed: str, errors: List[str]) -> str:
    errors_str = "\n".join(f"- {e}" for e in errors)
    return f"""You are fixing a caveman-compressed markdown file. Specific validation errors were found.

CRITICAL RULES:
- DO NOT recompress or rephrase the file
- ONLY fix the listed errors — leave everything else exactly as-is
- The ORIGINAL is provided as reference only (to restore missing content)
- Preserve caveman style in all untouched sections

ERRORS TO FIX:
{errors_str}

HOW TO FIX:
- Missing URL: find it in ORIGINAL, restore it exactly where it belongs in COMPRESSED
- Code block mismatch: find the exact code block in ORIGINAL, restore it in COMPRESSED
- Heading mismatch: restore the exact heading text from ORIGINAL into COMPRESSED
- Do not touch any section not mentioned in the errors

ORIGINAL (reference only):
{original}

COMPRESSED (fix this):
{compressed}

Return ONLY the fixed compressed file. No explanation.
"""


# ---------- Core Logic ----------


def compress_file(filepath: Path) -> bool:
    # Resolve and validate path
    filepath = filepath.resolve()
    MAX_FILE_SIZE = 500_000  # 500KB
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if filepath.stat().st_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large to compress safely (max 500KB): {filepath}")

    # Refuse files that look like they contain secrets or PII. Compressing ships
    # the raw bytes to the Anthropic API — a third-party boundary — so we fail
    # loudly rather than silently exfiltrate credentials or keys. Override is
    # intentional: the user must rename the file if the heuristic is wrong.
    if is_sensitive_path(filepath):
        raise ValueError(
            f"Refusing to compress {filepath}: filename looks sensitive "
            "(credentials, keys, secrets, or known private paths). "
            "Compression sends file contents to the Anthropic API. "
            "Rename the file if this is a false positive."
        )

    print(f"Processing: {filepath}")

    if not should_compress(filepath):
        print("Skipping (not natural language)")
        return False

    original_text = filepath.read_text(errors="ignore")
    backup_path = filepath.with_name(filepath.stem + ".original.md")

    # Check if backup already exists to prevent accidental overwriting
    if backup_path.exists():
        print(f"⚠️ Backup file already exists: {backup_path}")
        print("The original backup may contain important content.")
        print("Aborting to prevent data loss. Please remove or rename the backup file if you want to proceed.")
        return False

    # Step 1: Compress
    print("Compressing file...")
    compressed = compress_content(original_text)

    # Save original as backup, write compressed to original path
    backup_path.write_text(original_text)
    filepath.write_text(compressed)

    # Step 2: Validate + Retry
    for attempt in range(MAX_RETRIES):
        print(f"\nValidation attempt {attempt + 1}")

        result = validate(backup_path, filepath)

        if result.is_valid:
            print("Validation passed")
            break

        print("❌ Validation failed:")
        for err in result.errors:
            print(f"   - {err}")

        if attempt == MAX_RETRIES - 1:
            # Restore original on failure
            filepath.write_text(original_text)
            backup_path.unlink(missing_ok=True)
            print("❌ Failed after retries — original restored")
            return False

        print("Fixing compressed file...")
        compressed = fix_content(original_text, compressed, result.errors)
        filepath.write_text(compressed)

    return True
