#!/usr/bin/env python3
"""Tool-call reliability + speed bench for an OpenAI-compatible server. Stdlib only.
usage: toolbench.py --base http://127.0.0.1:8080 --model NAME --out result.json [--reps 3]
"""
import argparse, json, time, urllib.request

TOOLS = [
    {"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city",
        "parameters": {"type": "object", "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["c", "f"]}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "set_light", "description": "Turn a smart light on or off, optionally set brightness",
        "parameters": {"type": "object", "properties": {"room": {"type": "string"}, "on": {"type": "boolean"}, "brightness": {"type": "integer", "minimum": 0, "maximum": 100}}, "required": ["room", "on"]}}},
    {"type": "function", "function": {"name": "restart_service", "description": "Restart a systemd service on a host",
        "parameters": {"type": "object", "properties": {"host": {"type": "string"}, "service": {"type": "string"}}, "required": ["host", "service"]}}},
    {"type": "function", "function": {"name": "create_reminder", "description": "Create a reminder",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "minutes_from_now": {"type": "integer"}}, "required": ["text", "minutes_from_now"]}}},
]

# (prompt, expected tool or None for "no tool", expected args subset)
CASES = [
    ("What's the weather in Sydney?", "get_weather", {"city": "Sydney"}),
    ("Turn off the living room light.", "set_light", {"room": "living room", "on": False}),
    ("Set the bedroom light to 30 percent brightness.", "set_light", {"room": "bedroom", "on": True, "brightness": 30}),
    ("Restart nginx on host web01.", "restart_service", {"host": "web01", "service": "nginx"}),
    ("Remind me to check the oven in 15 minutes.", "create_reminder", {"minutes_from_now": 15}),
    ("It is Fahrenheit I want. Weather in Tokyo?", "get_weather", {"city": "Tokyo", "unit": "f"}),
    ("Switch the kitchen light on at full brightness.", "set_light", {"room": "kitchen", "on": True, "brightness": 100}),
    ("Hi there, how are you today?", None, {}),
    ("What is 12 times 12?", None, {}),
    ("Please restart the grafana service on monitor01.", "restart_service", {"host": "monitor01", "service": "grafana"}),
]


def post(base, body, timeout=300):
    req = urllib.request.Request(base + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data, time.time() - t0


def norm(v):
    return v.strip().lower() if isinstance(v, str) else v


import re
def _coerce(v):
    """JSON-decode a parameter value when possible (numbers, bools, arrays, objects); else keep the string."""
    low = v.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    try:
        return json.loads(v)
    except Exception:
        return v


def parse_text_calls(text):
    """Parse <tool_call> blocks: JSON body or Qwen3.5 XML (<function=name><parameter=k>v</parameter>)."""
    out = []
    for blk in re.findall(r"<tool_call>(.*?)(?:</tool_call>|$)", text or "", re.S):
        blk = blk.strip()
        m = re.search(r"<function=([^>\s]+)>", blk)
        if m:
            args = {k: _coerce(v.strip()) for k, v in re.findall(r"<parameter=([^>]+)>\s*(.*?)\s*</parameter>", blk, re.S)}
            out.append({"function": {"name": m.group(1), "arguments": json.dumps(args)}})
            continue
        try:
            j = json.loads(blk)
            out.append({"function": {"name": j.get("name"), "arguments": json.dumps(j.get("arguments", {}))}})
        except Exception:
            out.append({"function": {"name": None, "arguments": "{bad"}})
    return out


def _split_top(body):
    parts, depth, cur, q = [], 0, "", None
    for ch in body:
        if q:
            cur += ch
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; cur += ch; continue
        if ch in "[{": depth += 1
        if ch in "]}": depth -= 1
        if ch == "," and depth == 0: parts.append(cur); cur = ""; continue
        cur += ch
    if cur.strip(): parts.append(cur)
    return parts


def parse_gemma_calls(text):
    """Gemma native: call:name{key:value,key:value}; handles nested braces/arrays and <|"|> string delimiters."""
    text = (text or "").replace('<|"|>', '"')
    out = []
    for m in re.finditer(r"call:(\w+)\{", text):
        i, depth = m.end(), 1
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0); i += 1
        body = text[m.end():i - 1]
        args = {}
        for part in _split_top(body):
            if ":" in part:
                k, v = part.split(":", 1)
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": v = v[1:-1]
                else: v = _coerce(v)
                args[k.strip()] = v
        out.append({"function": {"name": m.group(1), "arguments": json.dumps(args)}})
    return out


def parse_json_calls(text):
    """Fallback for models without <tool_call> tags (Llama 3.2, Gemma3, DeepSeek): find JSON objects with name + arguments/parameters.
    Strips <think> blocks and <|python_tag|>; scans balanced braces so code fences and prose around the JSON are fine."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).replace("<|python_tag|>", " ")
    out, i = [], 0
    while True:
        i = text.find("{", i)
        if i < 0:
            break
        depth, j, instr, esc = 0, i, False, False
        while j < len(text):
            c = text[j]
            if instr:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: break
            j += 1
        if depth != 0:
            break
        try:
            d = json.loads(text[i:j + 1])
        except Exception:
            i += 1
            continue
        cands = d if isinstance(d, list) else [d]
        hit = False
        for x in cands:
            if isinstance(x, dict) and isinstance(x.get("function"), dict):
                x = x["function"]
            if isinstance(x, dict) and isinstance(x.get("name"), str) and ("arguments" in x or "parameters" in x):
                a = x.get("arguments", x.get("parameters"))
                out.append({"function": {"name": x["name"], "arguments": json.dumps(a) if not isinstance(a, str) else a}})
                hit = True
        i = j + 1 if hit else i + 1
    return out


def score(msg, want_tool, want_args):
    calls = msg.get("tool_calls") or parse_text_calls(msg.get("content")) or parse_gemma_calls(msg.get("content")) or parse_json_calls(msg.get("content"))
    r = {"valid_json": True, "right_tool": False, "right_args": False, "n_calls": len(calls)}
    if want_tool is None:
        r["right_tool"] = r["right_args"] = len(calls) == 0
        return r
    if not calls:
        r["valid_json"] = False
        return r
    fn = calls[0].get("function", {})
    try:
        args = json.loads(fn.get("arguments") or "{}") if isinstance(fn.get("arguments"), str) else (fn.get("arguments") or {})
    except Exception:
        r["valid_json"] = False
        return r
    r["right_tool"] = fn.get("name") == want_tool
    r["right_args"] = r["right_tool"] and all(norm(args.get(k)) == norm(v) for k, v in want_args.items())
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--model", default="m")
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args()
    rows = []
    # speed probe: plain generation
    d, dt = post(a.base, {"model": a.model, "messages": [{"role": "user", "content": "Write a 150 word paragraph about home labs."}], "max_tokens": 200, "temperature": 0, "reset_context": True})
    u = d.get("usage", {})
    speed = {"seconds": round(dt, 2), "completion_tokens": u.get("completion_tokens"), "tok_per_s": round(u.get("completion_tokens", 0) / dt, 2) if u.get("completion_tokens") else None}
    print("speed", speed, flush=True)
    for rep in range(a.reps):
        for prompt, tool, args in CASES:
            body = {"model": a.model, "messages": [{"role": "system", "content": "You are a home automation agent. Use tools when appropriate."}, {"role": "user", "content": prompt}],
                    "tools": TOOLS, "temperature": 0, "max_tokens": 400, "reset_context": True}
            try:
                d, dt = post(a.base, body)
                msg = d["choices"][0]["message"]
                s = score(msg, tool, args)
                s.update(prompt=prompt, secs=round(dt, 2), raw=(msg.get("content") or "")[:600], err=None)
            except Exception as e:
                s = {"prompt": prompt, "valid_json": False, "right_tool": False, "right_args": False, "n_calls": 0, "secs": None, "raw": "", "err": str(e)[:200]}
            rows.append(s)
            print(("PASS" if s["right_args"] else "FAIL"), prompt, s.get("secs"), s.get("err") or "", flush=True)
    n = len(rows)
    summ = {"n": n, "valid_json": sum(r["valid_json"] for r in rows) / n, "right_tool": sum(r["right_tool"] for r in rows) / n,
            "right_args": sum(r["right_args"] for r in rows) / n, "avg_secs": round(sum(r["secs"] or 0 for r in rows) / n, 2), "speed": speed}
    print("SUMMARY", json.dumps(summ), flush=True)
    json.dump({"summary": summ, "rows": rows}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
