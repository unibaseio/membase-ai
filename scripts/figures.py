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


def steps() -> str:
    items = [("1 · Install", "pip / npm install membase-ai"), ("2 · Integrate", "MCP, or the client in your code"),
             ("3 · Manage", "web app or the membase CLI"), ("4 · Retrieve", "search() and ask() at runtime")]
    w, gap = 186, 32
    body = []
    for i, (title, sub) in enumerate(items):
        x = i * (w + gap)
        body.append(_box(x, 8, w, 70, title, [sub], solid=i % 2 == 0))
        if i < len(items) - 1:
            body.append(_arrow(x + w + 4, 43, x + w + gap - 4, 43))
    return _svg(4 * w + 3 * gap, 86, "".join(body), "Install, integrate, manage, retrieve")


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
    rows = [("A conversation", "dated episodes", "one per topic, per speaker"),
            ("A document", "a topic tree", "text, or a web page by url"),
            ("An agent trace", "cases and skills", "membase agent ingest (local)")]
    body = ['<text class="t" x="0" y="18">What the local engine makes of what you add</text>']
    for i, (src, dst, note) in enumerate(rows):
        y = 36 + i * 72
        body.append(_box(0, y, 250, 56, src, solid=True))
        body.append(_arrow(254, y + 28, 352, y + 28))
        body.append(_box(356, y, 250, 56, dst))
        body.append(f'<text class="s" x="626" y="{y + 33}">{note}</text>')
    body.append(f'<text class="s" x="0" y="{36 + 3 * 72 + 8}">search() returns episodes and document topics; '
                f'membase --local agent search reads cases and skills.</text>')
    return _svg(840, 36 + 3 * 72 + 16, "".join(body), "Conversations, documents and agent traces")


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


FIGURES = {"steps": steps, "architecture": architecture, "operations": operations,
           "memory-types": memory_types, "mcp": mcp}


if __name__ == "__main__":
    for name, fn in FIGURES.items():
        (ASSETS / f"{name}.svg").write_text(fn())
        print(f"assets/{name}.svg")
