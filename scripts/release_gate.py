"""Release safety checks for the TradeNodeX open-source package.

The script intentionally scans only project-owned files. Dependency folders and
generated artifacts are excluded because they are not part of the source release.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    ".vite",
    ".cache",
    "venv",
    ".venv",
}

EXCLUDED_FILES = {
    "copytrading.db",
}

SENSITIVE_PATTERNS = {
    "private-key-block": r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----",
    "aws-access-key": r"AKIA[0-9A-Z]{16}",
    "probable-secret-assignment": r"(?i)(?:api[_-]?secret|secret[_-]?key|private[_-]?key)\s*[:=]\s*[\"'][^\"']{16,}[\"']",
}

RESIDUAL_PATTERNS = {
    "third-party-product-reference": "|".join(
        re.escape(value)
        for value in (
            "TV" + "-Hub",
            "Gem" + "ini",
            "AI" + " Studio",
            "Bloom" + "berg",
            "g" + "pt",
            "open" + "AI",
            "Open" + "AI",
            "Co" + "dex",
            "co" + "dex",
        )
    ),
}


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if parts & EXCLUDED_DIRS:
            continue
        if path.name in EXCLUDED_FILES:
            continue
        files.append(path)
    return files


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def scan(patterns: dict[str, str]) -> list[str]:
    findings: list[str] = []
    compiled = {name: re.compile(pattern) for name, pattern in patterns.items()}
    for path in iter_source_files():
        text = read_text(path)
        rel = path.relative_to(ROOT)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name, pattern in compiled.items():
                if pattern.search(line):
                    findings.append(f"{rel}:{line_no}: {name}")
    return findings


def main() -> int:
    findings = scan(SENSITIVE_PATTERNS) + scan(RESIDUAL_PATTERNS)
    if findings:
        print("Release gate failed:")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("Release gate passed: no blocked secrets or residual references found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
