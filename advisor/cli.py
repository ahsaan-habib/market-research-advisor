from __future__ import annotations

import argparse
import asyncio

from .research import research
from .sources import internal


def main() -> None:
    ap = argparse.ArgumentParser(prog="advisor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="index internal_docs/")
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--show-plan", action="store_true")
    args = ap.parse_args()
    if args.cmd == "index":
        print(f"indexed {internal.index()} internal passages")
        return
    r = asyncio.run(research(args.question))
    if args.show_plan:
        print("plan:", r.plan.model_dump_json(indent=2), "\n")
    print(r.brief)


if __name__ == "__main__":
    main()
