#!/usr/bin/env python3
"""Writes the SVG charts in ../charts from the numbers in the write-up (stdlib only)."""
import os, html

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "charts")
os.makedirs(OUT, exist_ok=True)
BG, FG, MUTE, LINE, QW, OTHER, COLD, TRACK = "#ffffff", "#13201b", "#53645c", "#d6ddd8", "#0a7a5c", "#9aa89f", "#c5cfc8", "#eef2ee"
FONT = "font-family:ui-monospace,Menlo,Consolas,monospace"


def save(name, w, h, body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
           f'<rect width="{w}" height="{h}" fill="{BG}"/>'
           f'<style>text{{{FONT};fill:{FG}}} .m{{fill:{MUTE}}}</style>{body}</svg>')
    open(os.path.join(OUT, name), "w").write(svg)


def bars(name, title, rows, maxv):
    lw, bw, rh, top = 190, 420, 24, 52
    w, h = lw + bw + 90, top + rh * len(rows) + 22
    b = [f'<text x="16" y="28" font-size="15" font-weight="700">{html.escape(title)}</text>']
    for i, (n, v, qwen) in enumerate(rows):
        y = top + i * rh
        b.append(f'<text x="{lw-8}" y="{y+14}" font-size="12" text-anchor="end">{html.escape(n)}</text>')
        b.append(f'<rect x="{lw}" y="{y+3}" width="{bw}" height="14" fill="{TRACK}" rx="2"/>')
        b.append(f'<rect x="{lw}" y="{y+3}" width="{bw*v/maxv:.1f}" height="14" fill="{QW if qwen else OTHER}" rx="2"/>')
        b.append(f'<text x="{lw+bw+8}" y="{y+14}" font-size="12">{v:g}</text>')
    b.append(f'<text x="16" y="{h-6}" font-size="10" class="m">green = Qwen family, grey = other families</text>')
    save(name, w, h, "".join(b))


speed = [("Qwen3-0.6B", 17.8), ("Llama3.2-1B", 12.8), ("Gemma3-1B", 12.7), ("DeepSeek-R1-1.5B", 10.6), ("Qwen3-1.7B", 10.5),
         ("Qwen3.5-2B", 9.88), ("Gemma4-E2B", 6.51), ("Llama3.2-3B", 5.95), ("Qwen3-4B", 4.85), ("Qwen3.5-4B", 4.47),
         ("Gemma3-4B", 3.87), ("Gemma3n-E4B", 3.33), ("DeepSeek-R1-7B", 2.90), ("Qwen3-8B", 2.44), ("Qwen3.5-9B", 2.16)]
hard = [("Qwen3-8B", 18), ("Qwen3-4B", 17), ("Qwen3.5-4B", 16), ("Qwen3.5-2B", 16), ("Qwen3-1.7B", 14), ("Qwen3-0.6B", 14),
        ("Gemma3-4B", 12), ("Llama3.2-3B", 10), ("Gemma3n-E4B", 8), ("Gemma3-1B", 5), ("Llama3.2-1B", 5), ("DeepSeek-R1 (both)", 3)]
agent = [("Qwen3.5-9B", 13), ("Qwen3.5-4B", 8), ("Qwen3-8B", 6), ("Qwen3-4B (16k)", 5), ("Qwen3.5-2B", 4),
         ("Qwen3-0.6B", 3), ("Qwen3-1.7B", 1), ("Gemma3n-E4B", 0)]
isq = lambda n: n.startswith("Qwen")
bars("decode-speed.svg", "Decode speed (tokens per second)", [(n, v, isq(n)) for n, v in speed], 18)
bars("hard-suite.svg", "Hard tool-call suite (of 18 cases)", [(n, v, isq(n)) for n, v in hard], 18)
bars("agent-tasks.svg", "Agent tasks passed (of 14)", [(n, v, isq(n)) for n, v in agent], 14)

# speed vs accuracy scatter
pts = [("Qwen3-0.6B", 17.8, 14), ("Qwen3-1.7B", 10.5, 14), ("Qwen3.5-2B", 9.88, 16), ("Qwen3-4B", 4.85, 17), ("Qwen3.5-4B", 4.47, 16),
       ("Qwen3-8B", 2.44, 18), ("Gemma3-4B", 3.87, 12), ("Llama3.2-3B", 5.95, 10), ("Gemma3n-E4B", 3.33, 8), ("Gemma3-1B", 12.7, 5),
       ("Llama3.2-1B", 12.8, 5), ("DeepSeek-R1-1.5B", 10.6, 3), ("DeepSeek-R1-7B", 2.9, 3)]
off = {"Qwen3.5-4B": (8, 13), "Gemma3-4B": (8, 13), "Gemma3-1B": (-8, -9), "Qwen3.5-2B": (8, -9), "Qwen3-0.6B": (8, -8),
       "Qwen3-1.7B": (8, -8), "Qwen3-4B": (8, -8), "Llama3.2-1B": (8, -9)}
W, H, L, R, T, B = 680, 400, 56, 24, 40, 48
sx = lambda x: L + x / 20 * (W - L - R)
sy = lambda y: H - B - y / 18 * (H - B - T)
b = ['<text x="16" y="24" font-size="15" font-weight="700">Decode speed vs hard-suite score</text>']
for yv in (0, 6, 12, 18):
    b.append(f'<line x1="{L}" x2="{W-R}" y1="{sy(yv):.1f}" y2="{sy(yv):.1f}" stroke="{LINE}"/><text x="{L-8}" y="{sy(yv)+4:.1f}" font-size="11" text-anchor="end" class="m">{yv}</text>')
for xv in (0, 5, 10, 15, 20):
    b.append(f'<text x="{sx(xv):.1f}" y="{H-B+18}" font-size="11" text-anchor="middle" class="m">{xv}</text>')
b.append(f'<text x="{(L+W-R)/2}" y="{H-8}" font-size="11" text-anchor="middle" class="m">tokens per second (faster to the right)</text>')
b.append(f'<text transform="translate(14 {(T+H-B)/2}) rotate(-90)" font-size="11" text-anchor="middle" class="m">hard suite, of 18</text>')
for n, x, y in pts:
    dx, dy = off.get(n, (8, 4))
    a = "end" if dx < 0 else "start"
    b.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="5" fill="{QW if isq(n) else OTHER}"/><text x="{sx(x)+dx:.1f}" y="{sy(y)+dy:.1f}" font-size="10.5" text-anchor="{a}">{n}</text>')
save("speed-vs-accuracy.svg", W, H, "".join(b))

# cache TTFT pairs
cache = [("Qwen3-0.6B", 4.9, 1.0), ("Qwen3-1.7B", 7.5, 0.95), ("Qwen3.5-2B", 16.5, 1.45), ("Qwen3-4B", 13.7, 3.5),
         ("Qwen3-8B", 22, 4.7), ("Gemma3n-E4B", 30.5, 4.8), ("Qwen3.5-4B", 30.5, 7.8), ("Qwen3.5-9B", 41, 8.6)]
lw, bw, rh, top = 150, 400, 28, 52
w, h = lw + bw + 130, top + rh * len(cache) + 28
b = ['<text x="16" y="28" font-size="15" font-weight="700">Time to first token: full prefill vs cache hit (s)</text>']
for i, (n, a, c) in enumerate(cache):
    y = top + i * rh
    b.append(f'<text x="{lw-8}" y="{y+15}" font-size="12" text-anchor="end">{n}</text>'
             f'<rect x="{lw}" y="{y+2}" width="{bw*a/41:.1f}" height="20" fill="{COLD}" rx="2"/>'
             f'<rect x="{lw}" y="{y+7}" width="{bw*c/41:.1f}" height="10" fill="{QW}" rx="2"/>'
             f'<text x="{lw+bw+8}" y="{y+15}" font-size="12">{a:g} s to {c:g} s</text>')
b.append(f'<text x="16" y="{h-8}" font-size="10" class="m">grey = full prefill, green = cache hit; midpoints of the measured ranges, 1.2-1.6k token prompts</text>')
save("cache-ttft.svg", w, h, "".join(b))

# context latency
ctx = [(1055, 39), (2500, 91), (4000, 102), (6000, 155), (8000, 250), (12000, 506), (15000, 751)]
W, H, L, R, T, B = 680, 320, 56, 24, 40, 48
cx = lambda x: L + x / 16000 * (W - L - R)
cy = lambda y: H - B - y / 800 * (H - B - T)
b = ['<text x="16" y="24" font-size="15" font-weight="700">Qwen3.5-4B: time to answer vs prompt size (no cache)</text>']
for yv in (0, 200, 400, 600, 800):
    b.append(f'<line x1="{L}" x2="{W-R}" y1="{cy(yv):.1f}" y2="{cy(yv):.1f}" stroke="{LINE}"/><text x="{L-8}" y="{cy(yv)+4:.1f}" font-size="11" text-anchor="end" class="m">{yv}</text>')
for xv in (0, 4000, 8000, 12000, 16000):
    b.append(f'<text x="{cx(xv):.1f}" y="{H-B+18}" font-size="11" text-anchor="middle" class="m">{xv//1000}k</text>')
b.append(f'<text x="{(L+W-R)/2}" y="{H-8}" font-size="11" text-anchor="middle" class="m">prompt tokens</text>'
         f'<text transform="translate(14 {(T+H-B)/2}) rotate(-90)" font-size="11" text-anchor="middle" class="m">seconds</text>')
path = " ".join(("M" if i == 0 else "L") + f"{cx(x):.1f} {cy(y):.1f}" for i, (x, y) in enumerate(ctx))
b.append(f'<path d="{path}" fill="none" stroke="{QW}" stroke-width="2.5"/>')
for x, y in ctx:
    b.append(f'<circle cx="{cx(x):.1f}" cy="{cy(y):.1f}" r="4.5" fill="{QW}"/>')
b.append(f'<text x="{cx(15000)-8:.1f}" y="{cy(751)-10:.1f}" font-size="10.5" text-anchor="end">15k tokens: about 12 minutes</text>')
save("context-latency.svg", W, H, "".join(b))
print("ok")
