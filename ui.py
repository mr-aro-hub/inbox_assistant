"""
Presentation layer: the stylesheet and the small HTML builders the
Streamlit app renders. Kept out of main.py for the same reason the
Gemini calls live in llm_logic.py — so the person styling the app and
the person wiring up behaviour aren't editing the same file.

Nothing here talks to the LLM or holds state; every function takes
plain values and returns an HTML string.
"""

from html import escape
from urllib.parse import quote

# ---------- Palette ----------
# Priority / sentiment / confidence all reuse this ramp so a colour
# means the same thing everywhere in the app.

RED = "#eb5757"
ORANGE = "#f2994a"
GREEN = "#4cb782"
GREY = "#8a8f98"
DIM = "#3a3d44"

PRIORITY_COLOR = {
    "Urgent": RED,
    "High": ORANGE,
    "Normal": GREEN,
    "Low": GREY,
    "Unanalyzed": GREY,
}

# How many of the three bars in the priority glyph are lit.
PRIORITY_BARS = {"Urgent": 3, "High": 3, "Normal": 2, "Low": 1, "Unanalyzed": 0}

# How much of the group-header ring is filled.
PRIORITY_FILL = {"Urgent": 1.0, "High": 0.75, "Normal": 0.5, "Low": 0.25, "Unanalyzed": 0.0}

SENTIMENT_COLOR = {
    "Positive": GREEN,
    "Neutral": GREY,
    "Frustrated": ORANGE,
    "Urgent/Stressed": RED,
}

CONFIDENCE_COLOR = {"High": GREEN, "Medium": ORANGE, "Low": RED}


# ---------- Icons ----------

def bars_data_uri(priority: str) -> str:
    """Linear-style three-bar priority glyph, as a CSS-embeddable data URI."""
    color = PRIORITY_COLOR.get(priority, GREY)
    filled = PRIORITY_BARS.get(priority, 0)
    geometry = [(0, 7, 5), (5, 4, 8), (10, 0, 12)]

    rects = "".join(
        f'<rect x="{x}" y="{y}" width="3" height="{h}" rx="1" '
        f'fill="{color if i < filled else DIM}"/>'
        for i, (x, y, h) in enumerate(geometry)
    )
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 13 12">{rects}</svg>'
    return "data:image/svg+xml," + quote(svg, safe="")


def ring(priority: str, size: int = 14) -> str:
    """Progress-ring icon: outer track plus a wedge sized to the priority."""
    color = PRIORITY_COLOR.get(priority, GREY)
    portion = PRIORITY_FILL.get(priority, 0.0)
    circumference = 18.85  # 2 * pi * r, with r = 3

    return (
        f'<svg class="ring" viewBox="0 0 14 14" width="{size}" height="{size}">'
        f'<circle cx="7" cy="7" r="6" fill="none" stroke="{color}" '
        f'stroke-width="1.5" opacity="0.45"/>'
        f'<circle cx="7" cy="7" r="3" fill="none" stroke="{color}" stroke-width="6"'
        f' stroke-dasharray="{portion * circumference:.2f} {circumference}"'
        f' transform="rotate(-90 7 7)"/>'
        "</svg>"
    )


# ---------- Fragments ----------

def group_header(priority: str, count: int) -> str:
    return (
        '<div class="group">'
        f"{ring(priority)}"
        f'<span class="group-name">{escape(priority)}</span>'
        f'<span class="group-count">{count}</span>'
        "</div>"
    )


def section_label(text: str) -> str:
    return f'<div class="section">{escape(text)}</div>'


def detail_header(subject: str, sender_name: str, sender_email: str, timestamp: str) -> str:
    return (
        f'<h1 class="mail-subject">{escape(subject)}</h1>'
        '<div class="mail-meta">'
        f'<span class="mail-from">{escape(sender_name)}</span>'
        f'<span class="mail-addr">{escape(sender_email)}</span>'
        f'<span class="mail-time">{escape(timestamp.replace("T", " · "))}</span>'
        "</div>"
    )


def mail_body(body: str) -> str:
    return f'<div class="mail-body">{escape(body)}</div>'


def stat_row(items: list[tuple[str, str, str]]) -> str:
    """items: (label, value, colour). Rendered as flat inline stats."""
    cells = "".join(
        '<div class="stat">'
        f'<div class="stat-label">{escape(label)}</div>'
        f'<div class="stat-value"><span class="dot" style="background:{color}"></span>'
        f"{escape(value)}</div>"
        "</div>"
        for label, value, color in items
    )
    return f'<div class="stats">{cells}</div>'


def summary_block(summary: str, reason: str) -> str:
    return (
        f'<div class="summary">{escape(summary)}</div>'
        f'<div class="reason">{escape(reason)}</div>'
    )


def task_list(tasks: list[tuple[str, str | None]]) -> str:
    """tasks: (description, deadline or None)."""
    rows = "".join(
        '<div class="task">'
        '<span class="task-tick"></span>'
        f'<span class="task-desc">{escape(desc)}</span>'
        + (f'<span class="task-due">{escape(deadline)}</span>' if deadline else "")
        + "</div>"
        for desc, deadline in tasks
    )
    return f'<div class="tasks">{rows}</div>'


def confidence_line(level: str, reason: str) -> str:
    color = CONFIDENCE_COLOR.get(level, GREY)
    return (
        '<div class="conf">'
        f'<span class="dot" style="background:{color}"></span>'
        f'<span class="conf-level" style="color:{color}">Confidence: {escape(level)}</span>'
        f'<span class="conf-reason">{escape(reason)}</span>'
        "</div>"
    )


def callout(text: str, tone: str = "note") -> str:
    """tone: warn | ok | note — a hairline accent rule, not a filled box."""
    return f'<div class="callout {tone}">{escape(text)}</div>'


def source_row(subject: str, sender: str, email_id: str) -> str:
    return (
        '<div class="source">'
        f'<span class="source-id">{escape(email_id.upper())}</span>'
        f'<span class="source-subject">{escape(subject)}</span>'
        f'<span class="source-sender">{escape(sender)}</span>'
        "</div>"
    )


def when_label(start, end, all_day: bool) -> str:
    """Human-readable span for a calendar row."""
    if all_day:
        return f"{start.strftime('%a %d %b')} · all day"

    if start.date() == end.date():
        if end == start:
            return f"{start.strftime('%a %d %b')} · {start.strftime('%H:%M')}"
        return (
            f"{start.strftime('%a %d %b')} · "
            f"{start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        )

    return (
        f"{start.strftime('%d %b %H:%M')} → {end.strftime('%d %b %H:%M')}"
    )


def calendar_item(title: str, when: str, source: str) -> str:
    return (
        '<div class="cal-item">'
        f'<div class="cal-title">{escape(title)}</div>'
        f'<div class="cal-when"><span class="dot"></span>{escape(when)}</div>'
        + (f'<div class="cal-src">{escape(source)}</div>' if source else "")
        + "</div>"
    )


def workspace_header(name: str) -> str:
    return (
        '<div class="ws">'
        '<div class="ws-mark">'
        '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" '
        'stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="2" y="4" width="20" height="16" rx="2.5"/><path d="m3 7 9 6 9-6"/>'
        "</svg></div>"
        f'<div class="ws-name">{escape(name)}</div>'
        '<div class="ws-dot"></div>'
        "</div>"
    )


def health_score(score: int) -> str:
    color = GREEN if score >= 70 else ORANGE if score >= 40 else RED
    return (
        '<div class="score">'
        f'<span class="score-num" style="color:{color}">{score}</span>'
        '<span class="score-den">/100</span>'
        "</div>"
        '<div class="score-track">'
        f'<div class="score-fill" style="width:{score}%;background:{color}"></div>'
        "</div>"
    )


def health_stat(label: str, value: int, color: str) -> str:
    return (
        '<div class="hstat">'
        f'<span class="dot" style="background:{color}"></span>'
        f'<span class="hstat-label">{escape(label)}</span>'
        f'<span class="hstat-value">{value}</span>'
        "</div>"
    )


def row_rules(email_ids_to_priority: dict[str, str], selected_id: str) -> str:
    """
    Per-row CSS: the priority glyph is painted as a ::before background so it
    can live inside a Streamlit button, which only accepts a markdown label.
    """
    rules = [
        f'.st-key-select_{eid} button::before{{background-image:url("{bars_data_uri(pri)}");}}'
        for eid, pri in email_ids_to_priority.items()
    ]
    rules.append(f".st-key-select_{selected_id} button{{background:var(--row-on);}}")
    rules.append(
        f".st-key-select_{selected_id} button p:first-child{{color:var(--t1);font-weight:510;}}"
    )
    return "<style>" + "".join(rules) + "</style>"


# ---------- Stylesheet ----------

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;600&display=swap');

:root{
  --bg:#101012;
  --side:#0b0b0d;
  --t1:#f7f8f8;
  --t2:#8a8f98;
  --t3:#61656c;
  --line:rgba(255,255,255,.07);
  --line-soft:rgba(255,255,255,.045);
  --row-hover:rgba(255,255,255,.035);
  --row-on:rgba(255,255,255,.065);
  --accent:#5e6ad2;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}

html,body,[class*="st-emotion"]{
  font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  -webkit-font-smoothing:antialiased;
}
/* the rule above would otherwise swallow Streamlit's icon ligatures
   (collapse arrows, spinner) and print their names as literal text */
[data-testid="stIconMaterial"],[class*="stIconMaterial"],
.material-icons,.material-symbols-rounded,.material-symbols-outlined{
  font-family:'Material Symbols Rounded','Material Symbols Outlined',
              'Material Icons'!important;
}

[data-testid="stAppViewContainer"]{background:var(--bg);}
[data-testid="stHeader"]{display:none;}
[data-testid="stMainBlockContainer"],.block-container{
  padding:1.5rem 2rem 4rem;max-width:none;
}
[data-testid="stMain"]{background:var(--bg);}
footer,#MainMenu{display:none;}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{
  background:var(--side);border-right:1px solid var(--line);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:14px 12px;}
[data-testid="stSidebarCollapseButton"] button{color:var(--t3);}

.ws{display:flex;align-items:center;gap:9px;padding:2px 4px 14px;}
.ws-mark{
  width:22px;height:22px;border-radius:6px;background:var(--accent);
  display:flex;align-items:center;justify-content:center;flex:0 0 auto;
}
.ws-name{font-size:13.5px;font-weight:550;color:var(--t1);letter-spacing:-.01em;}
.ws-dot{
  width:7px;height:7px;border-radius:50%;background:var(--accent);
  margin-left:auto;box-shadow:0 0 0 2.5px rgba(94,106,210,.18);
}

.section{
  font-size:10.5px;font-weight:550;letter-spacing:.07em;text-transform:uppercase;
  color:var(--t3);padding:14px 4px 7px;
}

.score{display:flex;align-items:baseline;gap:3px;padding:2px 4px 0;}
.score-num{font-size:30px;font-weight:600;letter-spacing:-.03em;line-height:1.1;}
.score-den{font-size:12.5px;color:var(--t3);}
.score-track{
  height:3px;border-radius:2px;background:rgba(255,255,255,.07);
  margin:9px 4px 14px;overflow:hidden;
}
.score-fill{height:100%;border-radius:2px;transition:width .35s ease;}

.hstat{display:flex;align-items:center;gap:8px;padding:5px 4px;font-size:12.5px;}
.hstat-label{color:var(--t2);}
.hstat-value{margin-left:auto;color:var(--t1);font-variant-numeric:tabular-nums;}

.dot{width:6px;height:6px;border-radius:50%;flex:0 0 auto;display:inline-block;}

.side-note{font-size:11.5px;color:var(--t3);line-height:1.5;padding:2px 4px;}
.side-foot{
  font-size:11px;color:var(--t3);padding:12px 4px 0;margin-top:12px;
  border-top:1px solid var(--line-soft);
}

/* ---------- top bar ---------- */
.topbar{display:flex;align-items:center;gap:10px;padding:0 0 14px;}
.topbar-title{font-size:15.5px;font-weight:550;color:var(--t1);letter-spacing:-.015em;}
.topbar-count{
  font-size:12px;color:var(--t2);background:rgba(255,255,255,.055);
  padding:1px 7px;border-radius:5px;font-variant-numeric:tabular-nums;
}
.topbar-hint{margin-left:auto;font-size:11.5px;color:var(--t3);}

.rule{height:1px;background:var(--line);margin:4px 0 16px;}

/* ---------- ask ---------- */
.stTextInput label,.stTextArea label{
  font-size:11px!important;color:var(--t3)!important;font-weight:450!important;
  letter-spacing:.02em;
}
.stTextInput div[data-baseweb="input"],.stTextArea div[data-baseweb="textarea"]{
  background:rgba(255,255,255,.035)!important;border:1px solid var(--line)!important;
  border-radius:8px!important;transition:border-color .12s ease;
}
.stTextInput div[data-baseweb="input"]:focus-within,
.stTextArea div[data-baseweb="textarea"]:focus-within{
  border-color:rgba(94,106,210,.65)!important;box-shadow:0 0 0 3px rgba(94,106,210,.1);
}
.stTextInput input,.stTextArea textarea{
  background:transparent!important;color:var(--t1)!important;
  font-size:13.5px!important;caret-color:var(--accent);
}
.stTextArea textarea{line-height:1.6!important;font-size:13px!important;}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--t3)!important;}

.answer-wrap{border-top:1px solid var(--line);margin-top:18px;padding-top:16px;}
.answer{font-size:13.5px;line-height:1.65;color:var(--t1);max-width:70ch;}

.source{
  display:flex;align-items:center;gap:10px;padding:7px 2px;
  border-bottom:1px solid var(--line-soft);font-size:12.5px;
}
.source:last-child{border-bottom:none;}
.source-id{
  font-family:var(--mono);font-size:10.5px;color:var(--t3);
  min-width:26px;letter-spacing:.02em;
}
.source-subject{color:var(--t1);}
.source-sender{margin-left:auto;color:var(--t3);font-size:11.5px;}

/* ---------- calendar ---------- */
.cal-context{
  font-size:11px;color:var(--t3);padding:0 4px 8px;line-height:1.45;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.cal-item{padding:7px 4px;border-bottom:1px solid var(--line-soft);}
.cal-item:last-of-type{border-bottom:none;}
.cal-title{font-size:12.5px;color:var(--t1);line-height:1.4;}
.cal-when{
  display:flex;align-items:center;gap:6px;
  font-size:11px;color:var(--t2);margin-top:3px;
}
.cal-when .dot{background:var(--accent);}
.cal-src{font-size:10.5px;color:var(--t3);margin-top:3px;line-height:1.4;}

/* ---------- buttons ---------- */
.stButton>button,.stDownloadButton>button{
  background:transparent;border:1px solid transparent;color:var(--t1);
  border-radius:7px;font-weight:450;box-shadow:none!important;
  transition:background .12s ease,border-color .12s ease;
}
.stButton>button:hover,.stDownloadButton>button:hover{
  background:var(--row-hover);color:var(--t1);border-color:transparent;
}
.stButton>button:focus,.stButton>button:focus-visible,
.stDownloadButton>button:focus,.stDownloadButton>button:focus-visible{
  outline:none!important;
}
.stButton>button:active{transform:none;}

.st-key-calendar_btn button{
  width:100%;justify-content:flex-start;border:1px solid var(--line);
  background:rgba(255,255,255,.03);font-size:12.5px;padding:7px 12px;
}
.st-key-calendar_btn button:hover{
  background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.13);
}
.st-key-ics_dl button{
  width:100%;justify-content:center;background:var(--accent)!important;
  color:#fff!important;border:none!important;font-size:12px;
  padding:7px 12px;margin-top:4px;
}
.st-key-ics_dl button:hover{background:#6a75d9!important;}

.st-key-ask_inbox_btn button{
  background:var(--accent)!important;color:#fff!important;border:none!important;
  font-size:12.5px;font-weight:500;padding:9px 20px;border-radius:7px;
}
.st-key-ask_inbox_btn button:hover{background:#6a75d9!important;}

.st-key-analyze_btn button,.st-key-draft_btn button,.st-key-analyze_all button{
  border:1px solid var(--line);background:rgba(255,255,255,.03);
  font-size:12.5px;padding:7px 14px;color:var(--t1);
}
.st-key-analyze_btn button:hover,.st-key-draft_btn button:hover,
.st-key-analyze_all button:hover{
  background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.13);
}
.st-key-analyze_all button{width:100%;justify-content:flex-start;}

/* ---------- inbox rows ---------- */
.group{display:flex;align-items:center;gap:8px;padding:15px 10px 7px;}
.group .ring{flex:0 0 auto;}
.group-name{font-size:12.5px;font-weight:550;color:var(--t1);letter-spacing:-.005em;}
.group-count{font-size:11.5px;color:var(--t3);font-variant-numeric:tabular-nums;}

[class*="st-key-select_"] button{
  width:100%;position:relative;padding:8px 10px 8px 33px;border-radius:6px;
  justify-content:flex-start;min-height:0;
}
[class*="st-key-select_"] button::before{
  content:"";position:absolute;left:11px;top:12px;width:13px;height:12px;
  background-repeat:no-repeat;background-size:13px 12px;
}
/* the label is a flex row of nested spans — force it to stack as two lines */
[class*="st-key-select_"] button>div{width:100%;text-align:left;display:block;}
[class*="st-key-select_"] button>div>span{display:block;width:100%;}
[class*="st-key-select_"] button [data-testid="stMarkdownContainer"]{
  display:block;width:100%;
}
[class*="st-key-select_"] button p{
  margin:0!important;line-height:1.4;display:block;width:100%;
}
[class*="st-key-select_"] button p:first-child{
  font-size:13px;color:var(--t2);font-weight:450;letter-spacing:-.005em;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
[class*="st-key-select_"] button:hover p:first-child{color:var(--t1);}
[class*="st-key-select_"] button p:last-child{
  font-size:11px;color:var(--t3);margin-top:1px!important;
}
[class*="st-key-select_"] button code{
  font-family:var(--mono)!important;font-size:10px;color:var(--t3);
  background:transparent!important;padding:0!important;margin-right:7px;
  letter-spacing:.02em;
}

/* ---------- detail ---------- */
.mail-subject{
  font-size:21px!important;font-weight:550!important;color:var(--t1)!important;
  letter-spacing:-.022em;line-height:1.3;margin:0 0 9px!important;padding:0!important;
  max-width:46ch;
}
.mail-meta{display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-size:12px;}
.mail-from{color:var(--t1);font-weight:450;}
.mail-addr{color:var(--t3);}
.mail-time{color:var(--t3);margin-left:auto;font-variant-numeric:tabular-nums;}

.mail-body{
  font-size:13.5px;line-height:1.7;color:#c8ccd2;white-space:pre-wrap;
  max-width:68ch;padding:18px 0 4px;
}

.stats{display:flex;gap:34px;padding:2px 0 16px;}
.stat-label{
  font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--t3);font-weight:550;margin-bottom:5px;
}
.stat-value{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--t1);}

.summary{font-size:13.5px;line-height:1.65;color:var(--t1);max-width:68ch;}
.reason{font-size:11.5px;color:var(--t3);margin-top:6px;line-height:1.55;max-width:68ch;}

.tasks{padding:2px 0 4px;}
.task{
  display:flex;align-items:center;gap:10px;padding:8px 2px;
  border-bottom:1px solid var(--line-soft);font-size:13px;
}
.task:last-child{border-bottom:none;}
.task-tick{
  width:11px;height:11px;border-radius:50%;flex:0 0 auto;
  border:1.5px solid var(--t3);
}
.task-desc{color:var(--t1);}
.task-due{
  margin-left:auto;font-size:11px;color:var(--t2);
  background:rgba(255,255,255,.05);padding:2px 8px;border-radius:5px;white-space:nowrap;
}

.conf{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12.5px;padding:2px 0;}
.conf-level{font-weight:550;}
.conf-reason{color:var(--t2);}

.callout{
  font-size:12.5px;line-height:1.6;color:var(--t2);
  padding:8px 0 8px 13px;border-left:2px solid var(--t3);margin-top:12px;max-width:68ch;
}
.callout.warn{border-left-color:#f2994a;color:#e8c89e;}
.callout.ok{border-left-color:#4cb782;color:#a6d7bd;}

.empty{font-size:12.5px;color:var(--t3);padding:18px 0;line-height:1.6;}

hr,[data-testid="stDivider"]{border-color:var(--line)!important;}
[data-testid="stSpinner"] > div{font-size:12px;color:var(--t2);}
[data-testid="stVerticalBlock"]{gap:.55rem;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.35rem;}
::-webkit-scrollbar{width:9px;height:9px;}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.09);border-radius:5px;}
::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,.15);}
::-webkit-scrollbar-track{background:transparent;}
</style>
"""
