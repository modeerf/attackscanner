from __future__ import annotations

import argparse

from .db import connect, init_db, repair_j_prefixed_attackers


def main() -> None:
    parser = argparse.ArgumentParser(description="Find or repair OCR-added leading J characters in attacker names.")
    parser.add_argument("--apply", action="store_true", help="Apply repairs. Without this flag, only prints a dry run.")
    args = parser.parse_args()

    init_db()
    with connect() as conn:
        candidates = repair_j_prefixed_attackers(conn, apply=args.apply)

    if not candidates:
        print("No J-prefixed attacker candidates found.")
        return

    action = "Repaired" if args.apply else "Would repair"
    for item in candidates:
        server = item["server_id"] if item["server_id"] is not None else "-"
        alliance = item["attacker_alliance_tag"] or "-"
        print(
            f"{action}: server={server} alliance={alliance} "
            f"{item['old_name']} -> {item['new_name']} "
            f"({item['attack_count']} attack(s), ids {item['first_attack_id']}-{item['last_attack_id']})"
        )

    if not args.apply:
        print("\nDry run only. Re-run with --apply to update the database.")


if __name__ == "__main__":
    main()
