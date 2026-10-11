import json, random, sys
sys.path.insert(0,".")
from toolbench2 import TOOLS
from tokenizers import Tokenizer
tok = Tokenizer.from_file("tok4b.json")
rng = random.Random(7)
TOOLTOK = len(tok.encode(json.dumps(TOOLS)).ids)
print("tool schema tokens ~", TOOLTOK)
subj = ["The backup job","Our monitoring stack","The storage cluster","A firmware update","The network team","The nightly report","Our reverse proxy","The certificate renewal","The media server","A scheduled scrub","The container runtime","The DNS resolver"]
verb = ["was reviewed during","completed without errors after","raised a few questions in","was rescheduled following","was documented after","failed once before","was benchmarked ahead of","needed extra attention during"]
obj = ["the weekend maintenance window","last month's capacity review","the quarterly audit","a routine kernel upgrade","the disk replacement","the VLAN migration","the power outage drill","the wiki cleanup","the archive migration","the thermal inspection"]
tail = ["Nobody reported user impact.","The notes were filed under operations.","A follow-up is planned for next quarter.","Logs were kept for thirty days.","The owner signed off on the result.","No action items remain open.","The change was approved by two reviewers.","Graphs looked normal afterwards."]
decoys = ["The replica database host is named atlas-3.","The staging database host is named atlas-9.","The analytics database host is named atlas-12.","The old primary database host, now retired, was named atlas-1.","The backup database host is named atlas-5."]
NEEDLE = "The primary database host is named atlas-7."
def sent():
    return f"{rng.choice(subj)} {rng.choice(verb)} {rng.choice(obj)}. {rng.choice(tail)}"
SYSQ = "You are an operations assistant for a homelab. Use the provided tools when an action or lookup is needed. If required information is missing, ask the user. If no tool fits, say so."
Q_NEEDLE = "\n\nUsing the notes above, restart the postgres service on the primary database host."
Q_PLAIN = "\n\nUnrelated to the notes: turn off the kitchen light."
def build(target, question):
    base = len(tok.encode(SYSQ + question).ids) + TOOLTOK
    budget = max(0, target - base)
    sents = []
    while len(tok.encode(" ".join(sents)).ids) < budget:
        sents.extend(sent() for _ in range(20))
    # trim to budget
    while sents and len(tok.encode(" ".join(sents)).ids) > budget:
        sents.pop()
    return sents
items = []
for target in (0, 2500, 4000, 6000, 8000, 12000, 15000):
    d = {"target_tokens": target}
    for task, q in (("needle", Q_NEEDLE), ("plain", Q_PLAIN)):
        if target == 0:
            text = ("Notes: " + NEEDLE + " " + " ".join(decoys[:2])) if task == "needle" else ""
        else:
            sents = build(target, q)
            if task == "needle":
                k = len(sents)
                pos = sorted(rng.sample(range(k), min(len(decoys), k)))
                for p, dc in zip(pos, decoys): sents.insert(p, dc)
                sents.insert(k // 2, NEEDLE)
            text = "Notes:\n" + " ".join(sents)
        d[task] = text + q
        d["actual_tokens"] = len(tok.encode(SYSQ + d[task]).ids) + TOOLTOK
    items.append(d)
    print(target, d["actual_tokens"])
json.dump({"items": items}, open("ctx_prompts.json", "w"))
