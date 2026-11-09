import base64
import json
import unittest
from io import BytesIO
from unittest.mock import patch

import azure.functions as func
from PIL import Image, ImageDraw

from function_app import app


class AzureFunctionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.functions = {function.get_function_name(): function for function in app.get_functions()}

    def request(self, name, body=b"", content_type="application/json", params=None):
        request = func.HttpRequest(
            method="GET" if name == "health" else "POST",
            url="http://localhost/api/" + name.replace("_", "-"),
            headers={"Content-Type": content_type},
            params=params or {},
            body=body,
        )
        response = self.functions[name].get_user_function()(request)
        self.assertEqual(response.mimetype, "application/json")
        return response.status_code, json.loads(response.get_body())

    def test_routes_require_function_keys(self):
        self.assertEqual(set(self.functions), {"health", "solve", "solve_image"})
        for function in self.functions.values():
            trigger = function.get_bindings()[0].get_dict_repr()
            self.assertEqual(trigger["authLevel"], func.AuthLevel.FUNCTION)

    def test_health(self):
        self.assertEqual(self.request("health"), (200, {"status": "ok"}))

    def test_json_puzzle_upload(self):
        puzzle = {
            "a": {"capacity": 4, "layers": [{"color": "white", "depth": 2}]},
            "b": {"capacity": 4, "layers": [{"color": "white", "depth": 2}]},
        }
        status, response = self.request("solve", json.dumps(puzzle).encode())
        self.assertEqual(status, 200)
        self.assertEqual(response["solution"], [["a", "b"]])

    def test_image_upload_includes_png_and_matching_ids(self):
        image = Image.new("RGB", (400, 1000), (30, 20, 50))
        draw = ImageDraw.Draw(image)
        for left in (40, 240):
            draw.rectangle((left, 350, left + 100, 900), outline=(190, 190, 190), width=6)
            draw.rectangle((left + 7, 655, left + 93, 893), fill=(220, 30, 30))
        body = BytesIO()
        image.save(body, format="PNG")
        status, response = self.request(
            "solve_image", body.getvalue(), "image/png", {"strategy": "recursive"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["strategy"], "recursive")
        self.assertEqual(response["solution"], [["1", "2"]])
        self.assertEqual([bottle["id"] for bottle in response["bottles"]], ["1", "2"])
        with Image.open(BytesIO(base64.b64decode(response["annotated_image"]["data_base64"]))) as result:
            self.assertEqual(result.size, image.size)
            self.assertEqual(result.format, "PNG")

    def test_bad_requests_return_json_errors(self):
        cases = [
            ("solve", b"{", "application/json", {}, 400),
            ("solve", b"\xff", "application/json", {}, 400),
            ("solve", b"[]", "application/json", {}, 422),
            ("solve_image", b"image.png", "text/plain", {}, 415),
            ("solve_image", b"not an image", "image/png", {}, 422),
            ("solve_image", b"", "image/png", {}, 422),
            ("solve_image", b"not an image", "image/png", {"strategy": "unknown"}, 422),
        ]
        for name, body, content_type, params, expected_status in cases:
            with self.subTest(name=name, body=body, params=params):
                status, response = self.request(name, body, content_type, params)
                self.assertEqual(status, expected_status)
                self.assertIn("error", response)

    def test_upload_limit_is_enforced(self):
        with patch("function_app.MAX_BODY_BYTES", 3):
            self.assertEqual(self.request("solve_image", b"long", "image/png")[0], 422)

    def test_no_solution_returns_404(self):
        puzzle = {"a": {"capacity": 4, "layers": [{"color": "white", "depth": 1}]}}
        status, response = self.request("solve", json.dumps(puzzle).encode())
        self.assertEqual(status, 404)
        self.assertIsNone(response["solution"])

    def test_recursion_limit_returns_json_error(self):
        with patch("function_app.solve_request", side_effect=RecursionError):
            status, response = self.request("solve", b"{}")
        self.assertEqual(status, 500)
        self.assertIn("recursion limit", response["error"])


if __name__ == "__main__":
    unittest.main()
