"""Interpret a reviewed, read-only browser snapshot; never infer commands."""

import argparse
import json
import re
import sys


def interpret(snapshot):
    """Extract only resource IDs and explicit castle level; unknowns stay unknown."""
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be a JSON object")
    hints = snapshot.get("hints", snapshot.get("elements", []))
    if isinstance(hints, str):
        hints = json.loads(hints)
    if not isinstance(hints, list):
        raise ValueError("hints must be a list")
    resources = {}
    buildings = {}
    for hint in hints:
        if not isinstance(hint, dict):
            continue
        identifier = hint.get("id", "")
        text = str(hint.get("text", ""))
        if identifier in {"wood", "stone", "iron"} and re.fullmatch(r"\d[\d.]*", text.strip()):
            resources[identifier] = int(text.strip().replace(".", ""))
        match = re.match(r"^\s*Castelo\s*\(Nível\s+(\d+)\)", text)
        if match:
            buildings["castle"] = int(match.group(1))
    unknown = [key for key in ("wood", "stone", "iron") if key not in resources]
    if "castle" not in buildings:
        unknown.append("castle_level")
    unknown.extend(("queue", "capacity", "workers", "next_level_cost"))
    return {"world": snapshot.get("host"), "observation_status": "partial", "resources": resources,
            "buildings": buildings, "unknown": unknown, "commands": "disabled"}


def main():
    argparse.ArgumentParser(description="Read-only snapshot interpreter; accepts JSON on stdin").parse_args()
    print(json.dumps(interpret(json.load(sys.stdin)), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
