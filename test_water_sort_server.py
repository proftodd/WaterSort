import base64
import unittest
from email.message import Message
from http import HTTPStatus
from io import BytesIO
from unittest.mock import Mock

from PIL import Image, ImageDraw

from water_sort_server import WaterSortRequestHandler, solve_request


class WaterSortServerTests(unittest.TestCase):
    def post(self, path, body, content_type):
        handler = WaterSortRequestHandler.__new__(WaterSortRequestHandler)
        handler.path = path
        handler.headers = Message()
        handler.headers["Content-Type"] = content_type
        handler.headers["Content-Length"] = str(len(body))
        handler.rfile = BytesIO(body)
        handler.write_json = Mock()
        handler.do_POST()
        return handler.write_json.call_args.args

    def test_image_upload_parses_and_solves_encoded_images(self):
        image = Image.new("RGB", (400, 1000), (30, 20, 50))
        draw = ImageDraw.Draw(image)
        for left in (40, 240):
            draw.rectangle((left, 350, left + 100, 900), outline=(190, 190, 190), width=6)
            draw.rectangle((left + 7, 655, left + 93, 893), fill=(220, 30, 30))

        for format, content_type in (("PNG", "image/png"), ("JPEG", "image/jpeg")):
            with self.subTest(format=format):
                encoded = BytesIO()
                image.save(encoded, format=format)
                status, response = self.post(
                    "/solve-image?strategy=recursive", encoded.getvalue(), content_type
                )
                self.assertEqual(status, HTTPStatus.OK)
                self.assertEqual(response["solution"], [("1", "2")])
                self.assertEqual(response["pours"], 1)
                self.assertEqual(response["strategy"], "recursive")
                self.assertEqual(response["puzzle"], {
                    "1": {"capacity": 4, "layers": [{"color": "color_01", "depth": 2}]},
                    "2": {"capacity": 4, "layers": [{"color": "color_01", "depth": 2}]},
                })
                self.assertEqual(set(response["swatches"]), {"color_01"})
                self.assertEqual(response["bottles"], [
                    {"id": "1", "bounds": {"left": 40, "top": 350, "right": 140, "bottom": 900}},
                    {"id": "2", "bounds": {"left": 240, "top": 350, "right": 340, "bottom": 900}},
                ])
                annotation = response["annotated_image"]
                self.assertEqual(annotation["media_type"], "image/png")
                with Image.open(BytesIO(base64.b64decode(annotation["data_base64"], validate=True))) as result:
                    self.assertEqual(result.format, "PNG")
                    self.assertEqual(result.size, image.size)
                    self.assertEqual(result.getpixel((40, 350)), (255, 255, 255))
                    # Numbers occupy the empty neck inside each detected bottle.
                    neck = result.crop((65, 355, 115, 405))
                    self.assertTrue(any(color == (255, 255, 255) for _, color in neck.getcolors(2500)))

    def test_image_upload_rejects_invalid_image(self):
        status, response = self.post("/solve-image", b"not an image", "image/png")
        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertIn("valid image", response["error"])

    def test_image_upload_rejects_path_instead_of_bytes(self):
        status, _ = self.post("/solve-image", b'{"path": "image.png"}', "application/json")
        self.assertEqual(status, HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    def test_image_upload_rejects_incomplete_body(self):
        handler = WaterSortRequestHandler.__new__(WaterSortRequestHandler)
        handler.headers = Message()
        handler.headers["Content-Length"] = "100"
        handler.rfile = BytesIO(b"short")
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            handler.read_body()

    def test_solve_request_returns_solution_payload(self):
        puzzle = {
            "1": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
            "2": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
        }

        self.assertEqual(
            solve_request(puzzle),
            {
                "strategy": "bfs",
                "solution": [("1", "2")],
                "pours": 1,
            },
        )

    def test_solve_request_can_use_recursive_strategy(self):
        puzzle = {
            "1": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
            "2": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
        }

        self.assertEqual(solve_request(puzzle, "recursive")["solution"], [("1", "2")])

    def test_solve_request_rejects_unknown_strategy(self):
        with self.assertRaisesRegex(ValueError, "strategy must be"):
            solve_request({}, "random")


if __name__ == "__main__":
    unittest.main()
