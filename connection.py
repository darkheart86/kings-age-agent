"""Read-only KingsAge connectivity probe; never logs into or acts on an account."""

import argparse
import json
from urllib.parse import parse_qs, urlparse

import requests


def probe(world_url, session=None):
    """Report public help and whether an unauthenticated world page redirects to lobby."""
    parsed = urlparse(world_url)
    village_params = parse_qs(parsed.query, strict_parsing=True) if parsed.query else {}
    valid_village = not village_params or (list(village_params) == ["village"] and len(village_params["village"]) == 1 and village_params["village"][0].isdigit())
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".kingsage.gameforge.com") or parsed.hostname == "lobby.kingsage.gameforge.com" or parsed.username or parsed.password or parsed.port or parsed.path not in ("", "/") or parsed.fragment or not valid_village:
        raise ValueError("Use an HTTPS world URL under *.kingsage.gameforge.com, optionally with ?village=ID")
    base = f"https://{parsed.hostname}"
    client = session or requests.Session()
    help_response = client.get(base + "/help.php?m=buildings", timeout=20, allow_redirects=True)
    game_response = client.get(base + "/game.php?screen=main", timeout=20, allow_redirects=True)
    game_host = urlparse(game_response.url).hostname
    if game_host == "lobby.kingsage.gameforge.com":
        account_status = "authentication_required"
    elif game_host == parsed.hostname and game_response.status_code == 200:
        account_status = "authentication_unverified"
    else:
        account_status = "unavailable"
    return {
        "world": parsed.hostname,
        **({"village": village_params["village"][0]} if village_params else {}),
        "public_help": "available" if help_response.status_code == 200 and urlparse(help_response.url).hostname == parsed.hostname else "unavailable",
        "account_status": account_status,
        "game_http_status": game_response.status_code,
        "game_destination_host": game_host,
        "commands": "disabled",
    }


def main():
    parser = argparse.ArgumentParser(description="Read-only KingsAge connectivity probe")
    parser.add_argument("world_url", help="HTTPS URL of the game world (not credentials)")
    args = parser.parse_args()
    print(json.dumps(probe(args.world_url), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
