from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from water_sort_solver import solve_puzzle, solve_puzzle_recursive


JsonObject = dict[str, Any]


def solve_request(puzzle: JsonObject, strategy: str = "bfs") -> JsonObject:
    if strategy == "recursive":
        solution = solve_puzzle_recursive(puzzle)
    elif strategy == "bfs":
        solution = solve_puzzle(puzzle)
    else:
        raise ValueError("strategy must be 'bfs' or 'recursive'.")

    return {
        "strategy": strategy,
        "solution": solution,
        "pours": len(solution) if solution is not None else None,
    }


class WaterSortRequestHandler(BaseHTTPRequestHandler):
    server_version = "WaterSortHTTP/1.0"

    def do_GET(self) -> None:
        if self.path == "/health":
            self.write_json(HTTPStatus.OK, {"status": "ok"})
            return

        self.write_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        if parsed_url.path != "/solve":
            self.write_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        query = parse_qs(parsed_url.query)
        strategy = query.get("strategy", ["bfs"])[0]

        try:
            puzzle = self.read_json_body()
            response = solve_request(puzzle, strategy)
        except json.JSONDecodeError as error:
            self.write_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {error}"})
            return
        except ValueError as error:
            self.write_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(error)})
            return
        except RecursionError:
            self.write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Search exceeded Python's recursion limit."},
            )
            return

        status = HTTPStatus.OK if response["solution"] is not None else HTTPStatus.NOT_FOUND
        self.write_json(status, response)

    def read_json_body(self) -> JsonObject:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length header is required.")

        length = int(raw_length)
        body = self.rfile.read(length)
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        return payload

    def write_json(self, status: HTTPStatus, payload: JsonObject) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Water Sort solver HTTP server.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on.")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), WaterSortRequestHandler)
    print(f"Water Sort solver listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
