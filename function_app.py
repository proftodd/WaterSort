from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

import azure.functions as func

from water_sort_server import MAX_BODY_BYTES, solve_image_request, solve_request


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def json_response(payload: dict[str, Any], status: int = HTTPStatus.OK) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload), status_code=status, mimetype="application/json")


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return json_response({"status": "ok"})


@app.route(route="solve", methods=["POST"])
def solve(req: func.HttpRequest) -> func.HttpResponse:
    return handle_solve(req, image=False)


@app.route(route="solve-image", methods=["POST"])
def solve_image(req: func.HttpRequest) -> func.HttpResponse:
    return handle_solve(req, image=True)


def handle_solve(req: func.HttpRequest, *, image: bool) -> func.HttpResponse:
    try:
        strategy = req.params.get("strategy", "bfs")
        if strategy not in ("bfs", "recursive"):
            raise ValueError("strategy must be 'bfs' or 'recursive'.")

        body = req.get_body()
        if not 0 < len(body) <= MAX_BODY_BYTES:
            raise ValueError("Request body must be between 1 byte and 20 MiB.")

        if image:
            content_type = req.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if not content_type.startswith("image/"):
                return json_response(
                    {"error": "Send image bytes with an image/* Content-Type."},
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                )
            response = solve_image_request(body, strategy)
        else:
            puzzle = json.loads(body)
            if not isinstance(puzzle, dict):
                raise ValueError("Request body must be a JSON object.")
            response = solve_request(puzzle, strategy)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return json_response({"error": f"Invalid JSON: {error}"}, HTTPStatus.BAD_REQUEST)
    except ValueError as error:
        return json_response({"error": str(error)}, HTTPStatus.UNPROCESSABLE_ENTITY)
    except RecursionError:
        return json_response(
            {"error": "Search exceeded Python's recursion limit."},
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    status = HTTPStatus.OK if response["solution"] is not None else HTTPStatus.NOT_FOUND
    return json_response(response, status)
