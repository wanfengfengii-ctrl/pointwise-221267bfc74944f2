import argparse
import json
import sys
from warehouse import Warehouse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["ingest", "quarantine", "replay", "snapshot"])
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--record")
    parser.add_argument("--attempt")
    parser.add_argument("--payload")
    parser.add_argument("--reason", default="manual correction")
    parser.add_argument("--lose-response", action="store_true")
    parser.add_argument("--pause-at", choices=["staged", "warehouse_committed", "before_close", "after_close"])
    args = parser.parse_args()

    def hook(name):
        if name == args.pause_at:
            print(json.dumps({"hook": name}), flush=True)
            sys.stdin.readline()

    try:
        if args.command == "ingest":
            warehouse = Warehouse(args.warehouse)
            try:
                result = warehouse.accept(args.record, json.loads(args.payload))
            finally:
                warehouse.close()
        elif args.command == "replay":
            from replay import apply
            result = apply(args.warehouse, args.queue, args.record, args.attempt,
                           json.loads(args.payload), hook, args.lose_response)
        else:
            from queue_store import Queue
            queue = Queue(args.queue)
            try:
                if args.command == "quarantine":
                    queue.add(args.record, args.reason)
                    result = queue.rows()
                else:
                    warehouse = Warehouse(args.warehouse)
                    try:
                        result = {"events": warehouse.rows(), "tasks": queue.rows()}
                    finally:
                        warehouse.close()
            finally:
                queue.close()
        print(json.dumps(result, sort_keys=True, ensure_ascii=False), flush=True)
        return 0
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
