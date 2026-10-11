#!/usr/bin/env python3
"""Batch / procedure agent-loop bench. Simulated house, mock tool executor, end-state scoring. Stdlib only.
usage: toolbench3.py --base http://127.0.0.1:8080 --tag NAME --out res.json [--only S1,S2a]
"""
import argparse, copy, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toolbench2 as t2
from toolbench2 import fn, S, I, B, N, calls_of

TOOLS = [
    fn("set_light", "Turn a light on or off, optionally set brightness percent", {"room": S, "on": B, "brightness": I}, ["room", "on"]),
    fn("garage_door", "Open or close the garage door", {"action": {"type": "string", "enum": ["open", "close"]}}, ["action"]),
    fn("lock_door", "Lock or unlock a door", {"door": S, "action": {"type": "string", "enum": ["lock", "unlock"]}}, ["door", "action"]),
    fn("camera_record", "Start or stop recording on a camera", {"camera": S, "action": {"type": "string", "enum": ["start", "stop"]}}, ["camera", "action"]),
    fn("set_alarm", "Set the alarm system mode", {"mode": {"type": "string", "enum": ["arm_away", "arm_night", "disarm"]}}, ["mode"]),
    fn("get_device_status", "Read the current state of a device", {"device": {"type": "string", "enum": ["garage", "alarm", "front_door", "bath"]}}, ["device"]),
    fn("set_water_pressure", "Set bath water pressure", {"level": {"type": "string", "enum": ["low", "medium", "high"]}}, ["level"]),
    fn("set_water_heater", "Turn the bath water heater on or off with a target temperature in Celsius", {"on": B, "target_c": N}, ["on"]),
    fn("bath_tap", "Open or close the bath tap; fill_to_percent is the target fill level", {"action": {"type": "string", "enum": ["open", "close"]}, "fill_to_percent": I}, ["action"]),
    fn("set_thermostat", "Set a thermostat zone temperature in Celsius", {"zone": S, "temp": N}, ["zone", "temp"]),
    fn("play_music", "Play a playlist in a room at a volume 0-100", {"room": S, "playlist": S, "volume": I}, ["room", "playlist"]),
]
NAMES = {t["function"]["name"] for t in TOOLS}

SYSTEM = """You are the home controller. Execute every command the user gives, using the tools. Do all of the commands, do not skip any, do not do anything that was not asked.
You may call several tools in one reply.

PROCEDURES (always follow them exactly):
BATH: to run a bath you must do these steps in this order: (1) set_water_pressure level=low, (2) set_water_heater on=true with target_c (default 38 unless the user gives a temperature), (3) bath_tap action=open with fill_to_percent (default 80 unless the user gives a level). Never open the tap before the heater is on.
CONDITIONALS: if the user says "if X" you must check with get_device_status first, then act only if the condition is true.
When finished, reply with one short sentence summarising what you did."""

INIT = {"lights": {}, "garage": "open", "doors": {}, "recording": [], "alarm": "disarmed", "pressure": None,
        "heater": {"on": False, "target_c": None}, "tap": {"open": False, "fill": 0}, "thermostat": {}, "music": {}}


class House:
    def __init__(self, garage="open"):
        self.s = copy.deepcopy(INIT); self.s["garage"] = garage
        self.log = []; self.precond_errors = 0; self.unknown = 0; self.dupes = 0; self._seen = set()

    def run(self, name, a):
        key = json.dumps([name, a], sort_keys=True)
        if key in self._seen and name != "get_device_status":
            self.dupes += 1
        self._seen.add(key)
        s = self.s; self.log.append((name, a))
        try:
            if name == "set_light":
                s["lights"][str(a["room"]).lower()] = {"on": bool(a["on"]), "brightness": a.get("brightness")}
            elif name == "garage_door":
                s["garage"] = "closed" if a["action"] == "close" else "open"
            elif name == "lock_door":
                s["doors"][str(a["door"]).lower()] = "locked" if a["action"] == "lock" else "unlocked"
            elif name == "camera_record":
                c = str(a["camera"]).lower()
                if a["action"] == "start" and c not in s["recording"]: s["recording"].append(c)
                if a["action"] == "stop" and c in s["recording"]: s["recording"].remove(c)
            elif name == "set_alarm":
                s["alarm"] = a["mode"]
            elif name == "get_device_status":
                d = a["device"]
                if d == "bath":
                    return {"pressure": s["pressure"], "heater": s["heater"], "tap": s["tap"]}
                return {d: {"garage": s["garage"], "alarm": s["alarm"], "front_door": s["doors"].get("front door", s["doors"].get("front_door", "unlocked"))}[d]}
            elif name == "set_water_pressure":
                s["pressure"] = a["level"]
            elif name == "set_water_heater":
                if a["on"] and s["pressure"] != "low":
                    self.precond_errors += 1
                    return {"error": "precondition failed: set_water_pressure level=low must be done before the heater"}
                s["heater"] = {"on": bool(a["on"]), "target_c": a.get("target_c")}
            elif name == "bath_tap":
                if a["action"] == "open" and not s["heater"]["on"]:
                    self.precond_errors += 1
                    return {"error": "precondition failed: the water heater is off, turn it on first"}
                s["tap"] = {"open": a["action"] == "open", "fill": a.get("fill_to_percent", 80 if a["action"] == "open" else s["tap"]["fill"])}
            elif name == "set_thermostat":
                s["thermostat"][str(a["zone"]).lower()] = a["temp"]
            elif name == "play_music":
                s["music"][str(a["room"]).lower()] = {"playlist": str(a["playlist"]).lower(), "volume": a.get("volume")}
            else:
                self.unknown += 1
                return {"error": "unknown tool"}
        except KeyError as e:
            return {"error": "missing argument %s" % e}
        return {"ok": True}


def room_on(rooms, name, brightness=None):
    for r, v in rooms.items():
        if name in r and v["on"] and (brightness is None or v["brightness"] == brightness):
            return True
    return False


def room_off(rooms, name):
    return any(name in r and not v["on"] for r, v in rooms.items())


def has_kw(d, key, name):
    return any(name in k for k in d if True) if key is None else any(name in k for k in d)


# each check: (label, fn(state)->bool)
def checks_bath(temp, fill):
    return [("pressure=low", lambda s: s["pressure"] == "low"),
            (f"heater on {temp}C", lambda s: s["heater"]["on"] and s["heater"]["target_c"] is not None and abs(float(s["heater"]["target_c"]) - temp) < 0.6),
            (f"tap open fill {fill}", lambda s: s["tap"]["open"] and s["tap"]["fill"] == fill)]


SCENARIOS = {
    "S1_five": dict(
        garage="open",
        prompt="Turn on the kitchen light, close the garage door, start recording on the front_door camera, set the alarm to arm_away, and get the bathtub warmed up and filling.",
        checks=[("kitchen light on", lambda s: room_on(s["lights"], "kitchen")), ("garage closed", lambda s: s["garage"] == "closed"),
                ("recording front_door", lambda s: any("front" in c for c in s["recording"])), ("alarm arm_away", lambda s: s["alarm"] == "arm_away")] + checks_bath(38, 80),
        order=[("set_water_pressure", "set_water_heater"), ("set_water_heater", "bath_tap")]),
    "S2a_goodnight_open": dict(
        garage="open",
        prompt="Goodnight routine: turn the living room light off, turn the hallway light on at 20 percent, lock the front door, if the garage is open then close it, start recording on the driveway camera, arm the alarm for night, set the bedroom thermostat to 19, and run a bath at 40 degrees filled to 60 percent.",
        checks=[("living off", lambda s: room_off(s["lights"], "living")), ("hallway 20%", lambda s: room_on(s["lights"], "hallway", 20)),
                ("front door locked", lambda s: any("front" in d and v == "locked" for d, v in s["doors"].items())), ("garage closed", lambda s: s["garage"] == "closed"),
                ("recording driveway", lambda s: any("driveway" in c for c in s["recording"])), ("alarm arm_night", lambda s: s["alarm"] == "arm_night"),
                ("bedroom 19", lambda s: any("bed" in z and abs(float(v) - 19) < 0.1 for z, v in s["thermostat"].items()))] + checks_bath(40, 60),
        order=[("set_water_pressure", "set_water_heater"), ("set_water_heater", "bath_tap")], need_status_before="garage_door"),
    "S2b_goodnight_closed": dict(
        garage="closed",
        prompt="Goodnight routine: turn the living room light off, turn the hallway light on at 20 percent, lock the front door, if the garage is open then close it, start recording on the driveway camera, arm the alarm for night, set the bedroom thermostat to 19, and run a bath at 40 degrees filled to 60 percent.",
        checks=[("living off", lambda s: room_off(s["lights"], "living")), ("hallway 20%", lambda s: room_on(s["lights"], "hallway", 20)),
                ("front door locked", lambda s: any("front" in d and v == "locked" for d, v in s["doors"].items())), ("garage still closed", lambda s: s["garage"] == "closed"),
                ("recording driveway", lambda s: any("driveway" in c for c in s["recording"])), ("alarm arm_night", lambda s: s["alarm"] == "arm_night"),
                ("bedroom 19", lambda s: any("bed" in z and abs(float(v) - 19) < 0.1 for z, v in s["thermostat"].items()))] + checks_bath(40, 60),
        order=[("set_water_pressure", "set_water_heater"), ("set_water_heater", "bath_tap")], forbid_call="garage_door"),
    "S3_ten": dict(
        garage="open",
        prompt="Right, I am heading out and the kids need a bath running at 36 degrees to 50 percent before I go. Please: kitchen light off, porch light on, lock the front door and the back door, close the garage, record the driveway camera and the front_door camera, play the jazz playlist in the living room at volume 30, set the hallway thermostat to 17, and arm the alarm to arm_away.",
        checks=[("kitchen off", lambda s: room_off(s["lights"], "kitchen")), ("porch on", lambda s: room_on(s["lights"], "porch")),
                ("front locked", lambda s: any("front" in d and v == "locked" for d, v in s["doors"].items())), ("back locked", lambda s: any("back" in d and v == "locked" for d, v in s["doors"].items())),
                ("garage closed", lambda s: s["garage"] == "closed"), ("rec driveway", lambda s: any("driveway" in c for c in s["recording"])), ("rec front", lambda s: any("front" in c for c in s["recording"])),
                ("jazz living 30", lambda s: any("living" in r and "jazz" in v["playlist"] and v["volume"] == 30 for r, v in s["music"].items())),
                ("hallway 17", lambda s: any("hall" in z and abs(float(v) - 17) < 0.1 for z, v in s["thermostat"].items())), ("alarm arm_away", lambda s: s["alarm"] == "arm_away")] + checks_bath(36, 50),
        order=[("set_water_pressure", "set_water_heater"), ("set_water_heater", "bath_tap")]),
}


def order_ok(log, pairs):
    names = [n for n, _ in log]
    for a, b in pairs:
        if a in names and b in names:
            if names.index(a) > names.index(b):
                return False
        elif b in names and a not in names:
            return False
    return True


def run_scenario(a, key, sc, max_turns=10):
    house = House(sc["garage"])
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": sc["prompt"]}]
    t0 = time.time(); turns = 0; final = ""; first = True; status_idx = None
    for _ in range(max_turns):
        turns += 1
        body = {"model": a.tag, "messages": msgs, "tools": TOOLS, "temperature": 0, "max_tokens": 1200}
        if first: body["reset_context"] = True
        first = False
        try:
            m, dt = t2.post(a.base, body, timeout=1800)
        except Exception as e:
            final = "ERR " + str(e)[:100]; break
        cs = calls_of(m)
        if not cs:
            final = (m.get("content") or "")[:200]; break
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": []})
        for i, (n, ar) in enumerate(cs):
            if n not in NAMES:
                house.unknown += 1; res = {"error": "unknown tool"}
            else:
                if n == sc.get("need_status_before") and not any(x[0] == "get_device_status" and str(x[1].get("device")) == "garage" for x in house.log):
                    status_idx = "no_status_before_action"
                res = house.run(n, ar if isinstance(ar, dict) else {})
            msgs.append({"role": "tool", "content": json.dumps(res), "tool_call_id": "c%d" % len(msgs)})
    secs = time.time() - t0
    results = [(label, bool(f(house.s))) for label, f in sc["checks"]]
    missing = [l for l, ok in results if not ok]
    ord_ok = order_ok(house.log, sc.get("order", []))
    forbid = bool(sc.get("forbid_call")) and any(n == sc["forbid_call"] for n, _ in house.log)
    cond_ok = status_idx is None
    state_score = sum(ok for _, ok in results) / len(results)
    passed = not missing and ord_ok and not forbid and cond_ok and house.unknown == 0 and house.precond_errors == 0
    row = dict(id=key, passed=passed, state_score=round(state_score, 2), missing=missing, order_ok=ord_ok, forbidden_call_made=forbid,
               checked_status_first=cond_ok, precond_errors=house.precond_errors, unknown_tools=house.unknown, dupes=house.dupes,
               turns=turns, secs=round(secs, 1), calls=[n for n, _ in house.log], final=final.replace("\n", " "))
    print(("PASS" if passed else "FAIL"), key, "state=%.2f" % state_score, "order=%s" % ord_ok, "precond_err=%d" % house.precond_errors, "turns=%d" % turns, "%.0fs" % secs,
          "" if passed else "missing=%s" % missing, flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8080"); ap.add_argument("--tag", default="m"); ap.add_argument("--out", required=True); ap.add_argument("--only")
    a = ap.parse_args()
    keys = a.only.split(",") if a.only else list(SCENARIOS)
    rows = [run_scenario(a, k, SCENARIOS[k]) for k in keys]
    summ = {"suite": "batch", "scenarios": len(rows), "passed": sum(r["passed"] for r in rows),
            "avg_state_score": round(sum(r["state_score"] for r in rows) / len(rows), 3), "precond_errors": sum(r["precond_errors"] for r in rows)}
    print("SUMMARY3", json.dumps(summ), flush=True)
    json.dump({"summary": summ, "rows": rows}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
