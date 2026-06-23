"""
Checklist export — render a saved Checklist as plain text or PDF.

PDF generation uses PyMuPDF's Story/DocumentWriter API (already a dependency via
the form filler), which flows HTML content across pages automatically. No new
dependency is introduced.

Both renderers take a Checklist ORM object with its `items` relationship loaded.
"""

import html
import json
import logging
from datetime import datetime, timezone

from app.models.checklist import Checklist, ChecklistItem

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "Visa rules change frequently. This checklist is generated from retrieved "
    "policy sources and may be incomplete or outdated. Always verify every "
    "requirement directly with the relevant embassy or consulate before applying."
)


# ── Shared helpers ───────────────────────────────────────────────────────────


def _confidence_label(score) -> str:
    if score is None:
        return "n/a"
    pct = round(score * 100)
    band = "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"
    return f"{pct}% ({band})"


def _sources_list(checklist: Checklist) -> list[str]:
    if not checklist.sources:
        return []
    try:
        data = json.loads(checklist.sources)
    except (json.JSONDecodeError, TypeError):
        return []
    return [s for s in data if s]


def _item_tags(item: ChecklistItem) -> list[str]:
    tags: list[str] = []
    tags.append("Mandatory" if item.is_mandatory else "Optional")
    if item.is_conditional:
        note = f": {item.condition_note}" if item.condition_note else ""
        tags.append(f"Conditional{note}")
    if item.requires_translation:
        tags.append("Needs certified translation")
    if item.requires_notarization:
        tags.append("Needs notarization/attestation")
    return tags


# ── Plain text ───────────────────────────────────────────────────────────────


def render_text(checklist: Checklist) -> str:
    lines: list[str] = []
    lines.append(checklist.title or "Document Checklist")
    lines.append("=" * len(lines[0]))
    lines.append(
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    lines.append(f"Confidence: {_confidence_label(checklist.confidence_score)}")
    lines.append("")

    if not checklist.items:
        lines.append("(No document requirements were extracted.)")
    for idx, item in enumerate(checklist.items, start=1):
        mark = "[x]" if item.is_completed else "[ ]"
        lines.append(f"{mark} {idx}. {item.document_name}")
        if item.description:
            lines.append(f"      {item.description}")
        tags = _item_tags(item)
        if tags:
            lines.append(f"      ({' · '.join(tags)})")
        lines.append("")

    sources = _sources_list(checklist)
    if sources:
        lines.append("Sources:")
        for s in sources:
            lines.append(f"  - {s}")
        lines.append("")

    lines.append("WARNING: " + _DISCLAIMER)
    return "\n".join(lines)


# ── PDF ──────────────────────────────────────────────────────────────────────


def render_pdf(checklist: Checklist) -> bytes:
    import io

    import fitz  # PyMuPDF

    html_doc = _build_html(checklist)

    stream = io.BytesIO()
    writer = fitz.DocumentWriter(stream)
    story = fitz.Story(html=html_doc)
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (50, 50, -50, -50)  # 50pt margins

    more = 1
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()

    return stream.getvalue()


def _build_html(checklist: Checklist) -> str:
    title = html.escape(checklist.title or "Document Checklist")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    confidence = html.escape(_confidence_label(checklist.confidence_score))

    items_html = []
    if not checklist.items:
        items_html.append('<p class="desc">(No document requirements were extracted.)</p>')
    for idx, item in enumerate(checklist.items, start=1):
        mark = "[x]" if item.is_completed else "[ ]"
        name = html.escape(item.document_name)
        desc = html.escape(item.description or "")
        tags = html.escape(" · ".join(_item_tags(item)))
        items_html.append(
            f'<div class="item">'
            f'<div class="name">{mark} {idx}. {name}</div>'
            f'<div class="desc">{desc}</div>'
            f'<div class="tags">{tags}</div>'
            f"</div>"
        )

    sources = _sources_list(checklist)
    sources_html = ""
    if sources:
        lis = "".join(f"<li>{html.escape(s)}</li>" for s in sources)
        sources_html = f'<div class="section">Sources</div><ul>{lis}</ul>'

    return f"""<html>
<head><style>
  body {{ font-family: sans-serif; font-size: 11px; color: #111; }}
  h1 {{ font-size: 18px; margin: 0 0 2px 0; }}
  .meta {{ color: #555; font-size: 10px; margin-bottom: 12px; }}
  .item {{ margin-bottom: 10px; }}
  .name {{ font-weight: bold; font-size: 12px; }}
  .desc {{ color: #333; margin: 1px 0; }}
  .tags {{ color: #666; font-size: 9px; }}
  .section {{ margin-top: 14px; font-weight: bold; font-size: 12px; }}
  ul {{ margin: 4px 0; padding-left: 16px; }}
  li {{ color: #2563eb; font-size: 9px; word-break: break-all; }}
  .disclaimer {{ margin-top: 16px; color: #777; font-size: 9px; }}
</style></head>
<body>
  <h1>{title}</h1>
  <div class="meta">Generated {generated} &middot; Confidence {confidence}</div>
  {''.join(items_html)}
  {sources_html}
  <div class="disclaimer">&#9888; {html.escape(_DISCLAIMER)}</div>
</body>
</html>"""
