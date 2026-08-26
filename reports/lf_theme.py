"""Single source of truth for LinForensics report styling.

Every generated report — the internal test report and the customer-facing
sample — resolves its colours through these tokens, which are sampled from
liforensics.com. Change a value here and every artefact follows on the next
build.
"""
from __future__ import annotations

PALETTE = {
    # brand
    "indigo": "#4F46E5",
    "indigo-strong": "#4338CA",
    "indigo-deep": "#3730A3",
    "indigo-soft": "#EEF2FF",
    "indigo-tint": "#F5F6FF",
    "indigo-line": "#DDE1FB",
    # text
    "ink": "#0B1220",
    "ink-2": "#1E293B",
    "body": "#475569",
    "muted": "#64748B",
    "faint": "#94A3B8",
    # structure
    "line": "#E2E8F0",
    "line-soft": "#EFF2F7",
    "surface": "#FFFFFF",
    "canvas": "#F8FAFC",
    # status
    "pass": "#0E9F6E",
    "pass-soft": "#E7F7F1",
    "warn": "#B45309",
    "warn-soft": "#FDF3E3",
    "warn-line": "#F3DFBC",
    "fail": "#DC2626",
    "fail-soft": "#FEECEC",
    "fail-line": "#F8D4D4",
}

FONT_STACK = (
    "'Plus Jakarta Sans', 'Figtree', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
)
MONO_STACK = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Plus+Jakarta+Sans:wght@400;500;600;700;800&"
    'family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'
)

#: Public concern levels the engine can emit, mapped to a palette tone.
LEVEL_TONE = {
    "high concern": "fail",
    "moderate concern": "warn",
    "low concern": "pass",
    "insufficient information": "muted",
    "review recommended": "warn",
}


def tokens_css() -> str:
    """Render the palette and type stacks as CSS custom properties."""
    lines = [f"    --lf-{name}: {value};" for name, value in PALETTE.items()]
    lines.append(f"    --lf-font: {FONT_STACK};")
    lines.append(f"    --lf-mono: {MONO_STACK};")
    return "\n".join(lines)


def mark_svg(size: int = 16) -> str:
    """The LinForensics shield glyph, sized for a rounded-square lockup."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
        '<path d="M12 3l7 3v5.2c0 4.4-2.9 8.2-7 9.4-4.1-1.2-7-5-7-9.4V6l7-3z" '
        'fill="rgba(255,255,255,.16)" stroke="#fff" stroke-width="1.7" stroke-linejoin="round"/>'
        '<path d="M8.8 12.1l2.2 2.2 4.2-4.4" stroke="#fff" stroke-width="1.9" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


def document(head: str, body: str, title: str, description: str = "") -> str:
    """Wrap head/body fragments into a standalone HTML document."""
    desc = f'<meta name="description" content="{description}">\n' if description else ""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n{desc}{FONT_LINKS}\n{head}\n</head>\n"
        f"<body>{body}</body>\n</html>\n"
    )
