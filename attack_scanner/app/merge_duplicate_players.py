from __future__ import annotations

import argparse

from .db import connect, init_db, merge_duplicate_players


def main() -> None:
    parser = argparse.ArgumentParser(description="Find or merge duplicate player rows with the same server and normalized name.")
    parser.add_argument("--apply", action="store_true", help="Apply merges. Without this flag, only prints a dry run.")
    args = parser.parse_args()

    init_db()
    with connect() as conn:
        groups = merge_duplicate_players(conn, apply=args.apply)

    if not groups:
        print("No duplicate player groups found.")
        return

    action = "Merged" if args.apply else "Would merge"
    for group in groups:
        server = group["server_id"] if group["server_id"] is not None else "-"
        duplicate_ids = ", ".join(str(player_id) for player_id in group["duplicate_ids"])
        print(
            f"{action}: server={server} name={group['canonical_name']} "
            f"canonical_id={group['canonical_id']} duplicate_ids=[{duplicate_ids}] "
            f"attack_refs={group['attack_refs']}"
        )

    if not args.apply:
        print("\nDry run only. Re-run with --apply to merge duplicate players.")


if __name__ == "__main__":
    main()
