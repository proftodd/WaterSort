import unittest

from water_sort_server import solve_request


class WaterSortServerTests(unittest.TestCase):
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
