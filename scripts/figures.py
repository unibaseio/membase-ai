"""Render the README diagrams in assets/."""

from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"

BLUE, DEEP, LIGHT, PALE, GREY, INK = "#3E61FF", "#2A3FBF", "#9DB0FF", "#E3E8FF", "#8B949E", "#1F2328"
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'


def _svg(width: int, height: int, body: str, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{GREY}"/></marker></defs>'
            f'<style>text{{font-family:{FONT};fill:{GREY}}} .t{{font-size:15px;font-weight:600;fill:{BLUE}}}'
            f' .h{{font-size:15px;font-weight:700}} .s{{font-size:12.5px}} .m{{font-family:{MONO};font-size:12px}}'
            f' .w{{fill:#FFFFFF}} .k{{fill:{DEEP}}}</style>{body}</svg>\n')


def _box(x, y, w, h, title, lines=(), solid=False, mono=False):
    fill, cls = (BLUE, "w") if solid else (PALE, "k")
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}"/>',
           (f'<text class="h {cls}" x="{x + w / 2}" y="{y + (26 if lines else h / 2 + 5)}" '
            f'text-anchor="middle">{title}</text>')]
    for i, line in enumerate(lines):
        out.append(f'<text class="{"m" if mono else "s"} {cls}" x="{x + w / 2}" y="{y + 46 + i * 17}" '
                   f'text-anchor="middle">{line}</text>')
    return "".join(out)


def _arrow(x1, y1, x2, y2, label="", dy=-7):
    out = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{GREY}" stroke-width="1.6" marker-end="url(#a)"/>'
    if label:
        out += (f'<text class="s" x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 + dy}" '
                f'text-anchor="middle">{label}</text>')
    return out


def architecture() -> str:
    body = ['<text class="t" x="0" y="18">One client, two places for the memory</text>']
    body.append(_box(0, 40, 230, 112, "Your code", ["Python: Membase()", "TypeScript: new Membase()",
                                                    "CLI: membase …"], solid=True))
    body.append(_box(320, 34, 250, 76, "Hosted", ["api.app.membase.io/v1"], mono=True))
    body.append(_box(320, 136, 250, 76, "Local", ["membase-core in-process"], mono=True))
    body.append(_box(640, 34, 200, 76, "Your Membase account", ["containers · profile"]))
    body.append(_box(640, 136, 200, 76, "~/.membase", ["SQLite + vector index"], mono=True))
    body.append(_arrow(232, 76, 316, 72))
    body.append(_arrow(232, 120, 316, 172))
    body.append('<text class="m" x="274" y="60" text-anchor="middle">api key</text>'
                '<text class="m" x="250" y="168" text-anchor="middle">local=True</text>')
    body.append(_arrow(572, 72, 636, 72))
    body.append(_arrow(572, 174, 636, 174))
    body.append(_box(320, 238, 250, 62, "membase serve", ["127.0.0.1:8787/v1, same routes"], mono=True))
    body.append(f'<line x1="445" y1="238" x2="445" y2="216" stroke="{GREY}" stroke-width="1.6" '
                f'stroke-dasharray="4 4" marker-end="url(#a)"/>')
    body.append('<text class="s" x="0" y="268">Other languages and tools reach</text>'
                '<text class="s" x="0" y="285">local memory over HTTP:</text>')
    body.append(_arrow(212, 272, 316, 272))
    return _svg(840, 306, "".join(body), "The Membase client: hosted API or local engine")


def operations() -> str:
    groups = [
        ("Read", BLUE, [("list_containers", "containers.list()"), ("search_memories", "search()"),
                        ("get_profile", "profile()"), ("list_documents", "documents.list()"),
                        ("get_document", "documents.get()"), ("memory_rules", "rules()")]),
        ("Write", LIGHT, [("add_memory", "memories.add()"), ("add_document", "add()")]),
        ("Remove · needs confirm", "#F2A93B", [("delete_document", "documents.delete()"),
                                               ("forget_memory", "memories.forget()")]),
        ("Answer", DEEP, [("ask_agent", "ask()")]),
    ]
    col, row, width = 210, 40, 840
    body = ['<text class="t" x="0" y="18">The agent protocol: eleven operations, one method each</text>']
    for i, (name, color, ops) in enumerate(groups):
        x = i * col
        body.append(f'<rect x="{x}" y="34" width="{col - 12}" height="6" rx="3" fill="{color}"/>'
                    f'<text class="h k" x="{x}" y="64" style="fill:{INK}">{name}</text>')
        for j, (op, method) in enumerate(ops):
            y = 78 + j * row
            body.append(f'<rect x="{x}" y="{y}" width="{col - 12}" height="{row - 6}" rx="8" fill="{PALE}"/>'
                        f'<text class="m k" x="{x + 10}" y="{y + 15}">{op}</text>'
                        f'<text class="m" x="{x + 10}" y="{y + 29}">{method}</text>')
    return _svg(width, 78 + 6 * row + 4, "".join(body), "Agent protocol operations and client methods")


def memory_types() -> str:
    rows = [("A conversation", "dated episodes"), ("A document", "a topic tree"),
            ("An agent trace", "cases and skills")]
    body = ['<text class="t" x="0" y="18">What the local engine makes of what you add</text>']
    for i, (src, dst) in enumerate(rows):
        y = 36 + i * 72
        body.append(_box(0, y, 340, 56, src, solid=True))
        body.append(_arrow(344, y + 28, 496, y + 28))
        body.append(_box(500, y, 340, 56, dst))
    return _svg(840, 36 + 3 * 72 - 12, "".join(body), "Conversations, documents and agent traces")


def mcp() -> str:
    body = ['<text class="t" x="0" y="18">Any MCP client, the agent-protocol tools, hosted or local</text>']
    clients = ["Claude Code", "Cursor", "Codex", "any MCP client"]
    for i, c in enumerate(clients):
        body.append(_box(0, 34 + i * 52, 190, 42, c, solid=i < 3))
    body.append(_box(320, 40, 260, 76, "Hosted endpoint", ["api.app.membase.io/mcp-http"], mono=True))
    body.append(_box(320, 136, 260, 76, "membase --local mcp", ["stdio · ~/.membase"], mono=True))
    for i in range(4):
        y = 55 + i * 52
        body.append(f'<line x1="192" y1="{y}" x2="250" y2="{y}" stroke="{GREY}" stroke-width="1.6"/>')
    body.append(f'<line x1="250" y1="55" x2="250" y2="211" stroke="{GREY}" stroke-width="1.6"/>')
    body.append(_arrow(250, 78, 316, 78))
    body.append(_arrow(250, 174, 316, 174))
    body.append('<text class="s" x="283" y="128" text-anchor="middle">either</text>')
    tools = ["list_containers", "search_memories", "get_profile", "list_documents", "memory_rules",
             "add_memory", "add_document", "delete_document", "forget_memory", "ask_agent"]
    body.append(f'<rect x="640" y="34" width="200" height="190" rx="12" fill="{PALE}"/>'
                f'<text class="h k" x="740" y="58" text-anchor="middle">Tools</text>')
    for i, t in enumerate(tools):
        body.append(f'<text class="m k" x="656" y="{80 + i * 14.5}">{t}</text>')
    body.append(_arrow(582, 78, 636, 110))
    body.append(_arrow(582, 174, 636, 150))
    return _svg(840, 240, "".join(body), "MCP clients, hosted or local server, same tools")


def _logo(cx, cy, r):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{BLUE}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r + 9}" fill="none" stroke="{LIGHT}" stroke-width="2" opacity=".6"/>'
            f'<path d="M{cx - r * .32} {cy - r * .38} v{r * .32} M{cx + r * .12} {cy - r * .38} v{r * .32}" '
            f'stroke="#FFFFFF" stroke-width="{r * .1:.1f}" stroke-linecap="round"/>'
            f'<path d="M{cx - r * .55} {cy + r * .08} q{r * .55} {r * .62} {r * 1.1} {-r * .1}" fill="none" '
            f'stroke="#FFFFFF" stroke-width="{r * .1:.1f}" stroke-linecap="round"/>')


def hero() -> str:
    sources = ["Documents and pages", "Facts you state", "Chat exports", "Uploads and connected apps"]
    readers = ["Your app", "MCP clients", "Your assistant", "The command line"]
    body = []
    for i, (src, reader) in enumerate(zip(sources, readers)):
        y = 18 + i * 60
        body.append(_box(0, y, 230, 46, src))
        body.append(_arrow(234, y + 23, 352, 120 + (i - 1.5) * 14))
        body.append(_box(610, y, 230, 46, reader, solid=True))
        body.append(_arrow(488, 120 + (i - 1.5) * 14, 606, y + 23))
    body.append(_logo(420, 120, 46))
    body.append(f'<text class="h" x="420" y="206" text-anchor="middle" style="fill:{BLUE};font-size:17px">'
                f'One memory</text>')
    return _svg(840, 268, "".join(body), "Sources go into one memory that every AI and app reads")


def _code_card(title, lines, width=410, height=230):
    body = [f'<rect width="{width}" height="{height}" rx="14" fill="#151A30"/>',
            ('<circle cx="20" cy="20" r="5" fill="#FF5F57"/><circle cx="36" cy="20" r="5" fill="#FEBC2E"/>'
             '<circle cx="52" cy="20" r="5" fill="#28C840"/>'),
            f'<text x="{width / 2}" y="24" text-anchor="middle" style="font-size:12px;fill:#8B93B5">{title}</text>']
    y = 52
    for kind, text in lines:
        color = {"code": "#E6E9F5", "dim": "#7C86B2", "out": "#9DB0FF", "ok": "#7EE2A8", "gap": ""}[kind]
        if kind != "gap":
            text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body.append(f'<text x="18" y="{y}" style="font-family:{MONO};font-size:12px;fill:{color}" '
                        f'xml:space="preserve">{text}</text>')
        y += 17 if kind != "gap" else 9
    return body


def sdk_card() -> str:
    lines = [("code", "from membase import Membase"),
             ("code", "m = Membase()"), ("gap", ""),
             ("code", 'm.memories.add("We picked Postgres for the ledger",'),
             ("code", '                container="Engineering")'), ("gap", ""),
             ("code", 'for hit in m.search("ledger database")["results"]:'),
             ("code", '    print(hit["container_name"], hit["content"])'), ("gap", ""),
             ("out", "Engineering  We picked Postgres for the ledger")]
    return _svg(420, 210, "".join(_code_card("app.py", lines, width=420, height=210)), "Python SDK: add a memory, search it")


def mcp_card() -> str:
    lines = [("code", "$ claude mcp add --transport http membase \\"), ("code", "    https://api.app.membase.io/mcp-http \\"),
             ("code", '    --header "Authorization: Bearer $KEY"'),
             ("ok", "Added HTTP MCP server membase with URL: …"), ("gap", ""),
             ("code", '$ claude -p "Which database is the ledger on?"'), ("gap", ""),
             ("out", "Postgres: you picked it for the ledger service,"),
             ("out", "according to your Engineering memory.")]
    return _svg(420, 210, "".join(_code_card("Claude Code", lines, width=420, height=210)), "Claude Code reads the memory over MCP")


TW, TH = 820, 440
NIGHT = "#12162B"


def _tile(eyebrow, headline_lines, sub_lines, content, ox=0, oy=0, gid="t"):
    out = [f'<g transform="translate({ox},{oy})">',
           (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#E9EDFF"/><stop offset=".55" stop-color="#F6F7FD"/>'
            '<stop offset="1" stop-color="#E4E1FB"/></linearGradient></defs>'),
           f'<rect width="{TW}" height="{TH}" rx="22" fill="url(#{gid})"/>',
           f'<text x="40" y="58" style="font-family:{MONO};font-size:12px;letter-spacing:.14em;fill:{BLUE}">{eyebrow}</text>']
    for i, line in enumerate(headline_lines):
        out.append(f'<text x="40" y="{108 + i * 46}" style="font-size:42px;font-weight:800;letter-spacing:-.02em;'
                   f'fill:{NIGHT}">{line}</text>')
    y0 = 108 + len(headline_lines) * 46 - 10
    for i, line in enumerate(sub_lines):
        out.append(f'<text x="40" y="{y0 + i * 22}" style="font-size:15px;fill:#5B6280">{line}</text>')
    out.append(content)
    out.append("</g>")
    return "".join(out)


def _card(x, y, w, h, inner, dark=False):
    fill = NIGHT if dark else "#FFFFFF"
    return (f'<rect x="{x + 2}" y="{y + 7}" width="{w}" height="{h}" rx="14" fill="#2A3FBF" opacity=".07"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}"/>{inner}')


def _window(x, y, w, h, title, bubble_lines):
    inner = (f'<circle cx="{x + 18}" cy="{y + 18}" r="4" fill="#D5D9EA"/><circle cx="{x + 31}" cy="{y + 18}" r="4" fill="#D5D9EA"/>'
             f'<circle cx="{x + 44}" cy="{y + 18}" r="4" fill="#D5D9EA"/>'
             f'<text x="{x + 58}" y="{y + 22}" style="font-family:{MONO};font-size:11px;fill:#5B6280">{title}</text>'
             f'<rect x="{x + 22}" y="{y + 38}" width="{w - 44}" height="{18 * len(bubble_lines) + 16}" rx="10" fill="{BLUE}"/>')
    for i, line in enumerate(bubble_lines):
        inner += f'<text x="{x + 34}" y="{y + 60 + i * 18}" style="font-size:12.5px;fill:#FFFFFF">{line}</text>'
    return _card(x, y, w, h, inner)


def _connect(ox=0, oy=0):
    q = ["Which identity provider will the", "Acme pilot use, and when?"]
    inner = (f'<circle cx="62" cy="230" r="7" fill="{BLUE}"/><text x="76" y="234" style="font-size:13px;font-weight:700;fill:{NIGHT}">My Assistant</text>'
             f'<rect x="96" y="250" width="226" height="48" rx="10" fill="{BLUE}"/>')
    for i, line in enumerate(q):
        inner += f'<text x="106" y="{270 + i * 17}" style="font-size:12px;fill:#FFFFFF">{line}</text>'
    for i, line in enumerate(["Microsoft Entra ID (SAML), starting", "10 November. From your Acme memory."]):
        inner += f'<text x="62" y="{326 + i * 17}" style="font-size:12px;fill:{NIGHT}">{line}</text>'
    inner_rect = '<rect x="56" y="310" width="262" height="46" rx="10" fill="#F3F5FD"/>'
    c = _card(44, 206, 290, 170, inner_rect + inner)
    term = [("$ claude -p \"Which identity provider", "#E6E9F5"), ("  will the Acme pilot use, and when?\"", "#E6E9F5"),
            ("", ""), ("Microsoft Entra ID via SAML,", "#9DB0FF"), ("starting 10 November.", "#9DB0FF")]
    tin = (f'<circle cx="502" cy="224" r="4" fill="#FF5F57"/><circle cx="515" cy="224" r="4" fill="#FEBC2E"/>'
           f'<circle cx="528" cy="224" r="4" fill="#28C840"/><text x="640" y="228" text-anchor="middle" '
           f'style="font-family:{MONO};font-size:11px;fill:#7C86B2">Claude Code</text>')
    for i, (line, col) in enumerate(term):
        if line:
            tin += f'<text x="502" y="{256 + i * 18}" style="font-family:{MONO};font-size:11.5px;fill:{col}" xml:space="preserve">{line}</text>'
    c += _card(486, 206, 300, 170, tin, dark=True)
    c += (f'<path d="M336 291 C 380 291, 380 291, 384 291" stroke="{LIGHT}" stroke-width="2" stroke-dasharray="5 5" fill="none"/>'
          f'<path d="M456 291 L 484 291" stroke="{LIGHT}" stroke-width="2" stroke-dasharray="5 5" fill="none"/>')
    c += _logo(420, 291, 30)
    c += f'<text x="420" y="350" text-anchor="middle" style="font-family:{MONO};font-size:10.5px;fill:#5B6280">Acme pilot memory</text>'
    return _tile("CONNECT", ["Every AI. Same memory."], [], c, ox, oy, "tc")


def every_ai() -> str:
    return _svg(TW, TH, _connect(), "Every AI, same memory: the assistant and Claude Code answer from one memory")


FIGURES = {"architecture": architecture, "operations": operations,
           "memory-types": memory_types, "mcp": mcp, "hero": hero, "sdk-card": sdk_card,
           "mcp-card": mcp_card, "every-ai": every_ai}


if __name__ == "__main__":
    for name, fn in FIGURES.items():
        (ASSETS / f"{name}.svg").write_text(fn())
        print(f"assets/{name}.svg")
