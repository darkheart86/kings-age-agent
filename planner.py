"""Deterministic, read-only planner for a KingsAge castle goal."""

import argparse
import json
from pathlib import Path


def decide(state, mode="planning", goal_level=10):
    """Return the next proposed step; never execute game actions."""
    level = state["buildings"]["castle"]
    if level >= goal_level:
        return {"status": "complete", "action": None, "reason": "Castle goal confirmed in observed state"}
    if state.get("queue"):
        return {"status": "waiting", "action": None, "reason": "Construction in progress"}
    return _resolve(state, "castle", mode, frozenset())


def _resolve(state, building, mode, visited):
    if building in visited:
        return {"status": "blocked", "action": None, "reason": "Circular prerequisites"}
    details = state.get("next_levels", {}).get(building)
    if not details or details.get("level") != state["buildings"].get(building, 0) + 1:
        return {"status": "blocked", "action": None, "reason": f"Missing observed cost for next {building} level"}
    for required, minimum in details.get("requires", {}).items():
        if state["buildings"].get(required, 0) < minimum:
            return _resolve(state, required, mode, visited | {building})
    cost = details.get("cost")
    if not isinstance(cost, dict) or not cost:
        return {"status": "blocked", "action": None, "reason": f"Missing observed cost for {building}"}
    if any(amount > state["capacity"] for amount in cost.values()):
        if building == "warehouse":
            return {"status": "blocked", "action": None, "reason": "Warehouse upgrade exceeds current capacity"}
        return _resolve(state, "warehouse", mode, visited | {building})
    if all(state["resources"].get(resource, 0) >= amount for resource, amount in cost.items()):
        if "workers" in details and state.get("free_workers", -1) < details["workers"]:
            return {"status": "waiting", "action": None, "reason": "Insufficient free workers"}
        if details.get("enabled") is False:
            return {"status": "blocked", "action": None, "reason": "Live build button is unavailable; refresh and re-observe"}
        action = {"building": building, "level": details["level"]}
        permitted = mode == "autonomous" and building in {"castle", "warehouse"}
        return {"status": "ready" if permitted else "approval_required", "action": action}
    return {"status": "waiting", "action": None, "reason": "Insufficient resources"}


def main():
    parser = argparse.ArgumentParser(description="Read-only KingsAge planning preview")
    parser.add_argument("state", type=Path, help="Observed state in JSON format")
    parser.add_argument("--mode", choices=["planning", "autonomous"], default="planning")
    parser.add_argument("--goal", type=int, default=10)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8"))
    print(json.dumps(decide(state, args.mode, args.goal), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
