"""Render a GDPR export as a single self-contained, human-readable HTML file."""

import re
from html import escape

URI = re.compile(r"^/rest/v1/([a-z]+)/(\d+)/$")
ISO_DATETIME = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(:\d{2}(\.\d+)?)?")

# Keys that only mean something inside ActionKit.
HIDDEN = {
    "id",
    "resource_uri",
    "token",
    "akid",
    "rand_id",
    "opq_id",
    "import_id",
    "user",
    "user_detail",
    "cancel",
    "logintoken",
}

# Top-level export keys that are not data sections.
META = {"exported_at", "email", "user"}

DETAIL_SECTIONS = [
    ("location", "Location"),
    ("useroriginal", "Original address"),
]

LIST_SECTIONS = [
    ("actions", "Actions"),
    ("orders", "Donations"),
    ("orderrecurrings", "Recurring donations"),
    ("transactions", "Payments"),
    ("subscriptions", "Subscriptions"),
    ("subscriptionhistory", "Subscription history"),
    ("events", "Events hosted"),
    ("eventsignups", "Event sign-ups"),
    ("usergeofields", "Geographic data"),
]

# Values longer than this move out of table columns into a full-width row.
LONG_TEXT = 80

# Columns shown first in tables, when present.
PREFERRED_COLUMNS = [
    "created_at",
    "page",
    "action",
    "order",
    "list",
    "change",
    "type",
    "status",
    "total",
    "amount",
    "currency",
    "period",
]

LABELS = {
    "created_at": "Created",
    "updated_at": "Last updated",
    "page": "Campaign",
    "action": "Campaign",
    "order": "Campaign",
    "targeted": "Recipients",
    "ip_address": "IP address",
    "zip": "ZIP",
}

CSS = """
:root { color-scheme: light; }
body { font: 15px/1.5 system-ui, sans-serif; color: #1a1a1a; background: #fff;
       max-width: 960px; margin: 0 auto; padding: 24px 16px; }
h1 { font-size: 1.6em; margin-bottom: 0.2em; }
h2 { font-size: 1.2em; margin-top: 2em; border-bottom: 2px solid #ddd; padding-bottom: 4px; }
.meta { color: #555; margin-top: 0; }
.intro { background: #f4f4f4; padding: 12px 16px; border-radius: 6px; }
.empty { color: #777; font-style: italic; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 4px 16px; }
dt { font-weight: 600; }
dd { margin: 0; white-space: pre-wrap; }
.letter { border: 1px solid #e4e4e4; border-radius: 6px; padding: 8px 16px; margin: 12px 0; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid #e4e4e4; vertical-align: top; }
th { background: #f4f4f4; }
td:first-child { white-space: nowrap; }
tr:has(+ .detail) td { border-bottom: none; }
.detail td { white-space: pre-wrap; padding: 0 8px 8px 24px; color: #333; }
.detail p { margin: 2px 0; }
@media print { .scroll { overflow: visible; } h2 { break-after: avoid; } tr { break-inside: avoid; } }
"""

INTRO = (
    "This document lists the personal data WeMove Europe holds about you in "
    "our supporter database, as requested under Article 15 of the General "
    "Data Protection Regulation. Each section below shows one kind of record. "
    "Sections marked “No records” contain no data about you."
)


def ref_key(value) -> tuple[str, str] | None:
    """Normalise a resource URI to (kind, id), e.g. donationpage/53 -> page 53."""
    if not isinstance(value, str):
        return None
    match = URI.match(value)
    if not match:
        return None
    resource, ident = match.groups()
    if resource.endswith("page"):
        return "page", ident
    # Action subtypes (donationaction, ...) share IDs with core actions,
    # but "transaction" only happens to end in "action".
    if resource.endswith("action") and resource != "transaction":
        return "action", ident
    return resource, ident


def humanize(key: str) -> str:
    if key in LABELS:
        return LABELS[key]
    return key.replace("_", " ").strip().capitalize()


def display(value, labels) -> str | None:
    """Plain-text form of a value, or None if it should be hidden."""
    if value is None or value == "" or value == [] or value == {}:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str):
        if value.startswith("/rest/v1/"):
            return labels.get(ref_key(value))
        match = ISO_DATETIME.match(value)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return value
    if isinstance(value, dict):
        for key in ("description", "name", "title"):
            if value.get(key):
                return str(value[key])
        parts = [
            f"{humanize(k)}: {text}"
            for k, raw in value.items()
            if k not in HIDDEN and (text := display(raw, labels))
        ]
        return "; ".join(parts) or None
    if isinstance(value, list):
        parts = [v for item in value if (v := display(item, labels))]
        return ", ".join(parts) or None
    return str(value)


def visible_items(record: dict, labels) -> list[tuple[str, str]]:
    items = []
    for key, value in record.items():
        if key in HIDDEN:
            continue
        text = display(value, labels)
        if text is not None:
            items.append((key, text))
    return items


def render_dl(items: list[tuple[str, str]]) -> str:
    if not items:
        return '<p class="empty">No records</p>'
    rows = "".join(
        f"<dt>{escape(label)}</dt><dd>{escape(text)}</dd>" for label, text in items
    )
    return f"<dl>{rows}</dl>"


def render_profile(user: dict, labels) -> str:
    items = []
    for key, text in visible_items(user, labels):
        if key == "fields":
            continue
        items.append((humanize(key), text))
    for key, value in (user.get("fields") or {}).items():
        text = display(value, labels)
        if text is not None:
            items.append((humanize(key), text))
    return render_dl(items)


def detail_lines(record: dict, key: str, text: str, labels) -> list[tuple[str, str]]:
    """Lines for a record's full-width row; `fields` gets one line each."""
    if key == "fields":
        return [
            (humanize(k), t)
            for k, v in record["fields"].items()
            if (t := display(v, labels)) is not None
        ]
    return [(humanize(key), text)]


def render_table(records: list[dict], labels) -> str:
    rows = [(r, items) for r in records if (items := visible_items(r, labels))]
    if not rows:
        return '<p class="empty">No records</p>'
    keys = []
    for _, items in rows:
        for key, _ in items:
            if key not in keys:
                keys.append(key)
    # Free text such as comments would squash the table into tall narrow
    # rows, so it goes in a full-width row under its record instead.
    long_keys = {"fields"} | {
        key for _, items in rows for key, text in items if len(text) > LONG_TEXT
    }
    ordered = [k for k in PREFERRED_COLUMNS if k in keys]
    ordered += [k for k in keys if k not in ordered]
    ordered = [k for k in ordered if k not in long_keys]
    # Keys sharing a label (e.g. a recurring donation's action and order both
    # give its campaign) collapse into one column.
    columns = list(dict.fromkeys(humanize(k) for k in ordered))
    body = []
    for record, items in rows:
        merged, lines = {}, []
        for key, text in items:
            if key in long_keys:
                lines += detail_lines(record, key, text, labels)
            else:
                merged.setdefault(humanize(key), text)
        cells = "".join(f"<td>{escape(merged.get(c, ''))}</td>" for c in columns)
        body.append(f"<tr>{cells}</tr>")
        if lines:
            text = "".join(
                f"<p><strong>{escape(k)}:</strong> {escape(v)}</p>" for k, v in lines
            )
            body.append(
                f'<tr class="detail"><td colspan="{max(len(columns), 1)}">{text}</td></tr>'
            )
    head = "".join(f"<th>{escape(c)}</th>" for c in columns)
    return (
        f'<div class="scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def render_letters(actions: list[dict], labels, letters) -> str | None:
    """One entry per letter action: who it went to and what it said."""
    entries = []
    for action in actions:
        template = letters.get(ref_key(action.get("page")))
        if template is None and "targeted" not in action:
            continue
        items = [
            ("Date", display(action.get("created_at"), labels)),
            ("Campaign", display(action.get("page"), labels)),
            ("Recipients", display(action.get("targeted"), labels)),
            ("Letter text", template or None),
            (
                "Your comment",
                display((action.get("fields") or {}).get("comment"), labels),
            ),
        ]
        entries.append(
            f'<div class="letter">{render_dl([(k, v) for k, v in items if v])}</div>'
        )
    return "".join(entries) or None


def section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def render_html(export: dict, labels: dict, letters: dict | None = None) -> str:
    """Render an export (as built by `gdpr export`) to an HTML document.

    `labels` maps `ref_key()` tuples to display titles, e.g. page titles,
    and `letters` maps letter pages' `ref_key()`s to their letter template.
    """
    user = export.get("user", {})
    name = " ".join(
        p for p in (user.get("first_name"), user.get("last_name")) if p
    ) or export.get("email", "")
    exported = display(export.get("exported_at"), labels) or ""

    parts = [section("Profile", render_profile(user, labels))]
    known = META | {key for key, _ in DETAIL_SECTIONS + LIST_SECTIONS}
    for key, title in DETAIL_SECTIONS:
        if key in export:
            parts.append(
                section(
                    title,
                    render_dl(
                        [
                            (humanize(k), t)
                            for k, t in visible_items(export[key], labels)
                        ]
                    ),
                )
            )
    for key, title in LIST_SECTIONS:
        if key in export:
            parts.append(section(title, render_table(export[key], labels)))
        if key == "actions":
            body = render_letters(export.get("actions", []), labels, letters or {})
            if body:
                parts.append(section("Letters", body))
    for key, value in export.items():
        if key in known:
            continue
        if isinstance(value, list):
            parts.append(section(humanize(key), render_table(value, labels)))
        elif isinstance(value, dict):
            items = [(humanize(k), t) for k, t in visible_items(value, labels)]
            parts.append(section(humanize(key), render_dl(items)))

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Personal data export</title><style>{CSS}</style></head><body>"
        f"<h1>Personal data held about {escape(name)}</h1>"
        f'<p class="meta">{escape(export.get("email", ""))} · exported {escape(exported)}</p>'
        f'<p class="intro">{escape(INTRO)}</p>' + "".join(parts) + "</body></html>\n"
    )
