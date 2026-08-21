import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from water_sort_solver import (
    Layer,
    apply_pour,
    is_completed_bottle,
    is_solved,
    load_puzzle,
    normalize_puzzle,
    possible_pours,
    puzzle_key,
    solve_all_puzzles,
    solve_puzzle,
    solve_puzzle_recursive,
)


def apply_solution(puzzle, solution):
    state = normalize_puzzle(puzzle)
    for pour in solution:
        state = apply_pour(state, pour)

    return state


class WaterSortSolverTests(unittest.TestCase):
    def test_finds_all_solutions_for_matching_top_layers(self):
        puzzle = {
            "1": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
            "2": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
        }

        self.assertEqual(solve_puzzle(puzzle), [("1", "2")])
        self.assertEqual(
            solve_all_puzzles(puzzle),
            [[("1", "2")], [("2", "1")]],
        )
        self.assertTrue(is_solved(apply_solution(puzzle, solve_puzzle_recursive(puzzle))))

    def test_empty_destination_is_valid(self):
        puzzle = {
            "1": {
                "capacity": 3,
                "layers": [
                    {"color": "Red", "depth": 1},
                    {"color": "Blue", "depth": 1},
                ],
            },
            "2": {"capacity": 2, "layers": []},
        }

        self.assertEqual(possible_pours(normalize_puzzle(puzzle)), [("1", "2")])

    def test_uniform_source_does_not_pour_into_empty_destination(self):
        puzzle = {
            "1": {"capacity": 3, "layers": [{"color": "Blue", "depth": 2}]},
            "2": {"capacity": 3, "layers": []},
        }

        self.assertEqual(possible_pours(normalize_puzzle(puzzle)), [])

    def test_completed_bottles_are_not_valid_sources(self):
        puzzle = {
            "1": {"capacity": 2, "layers": [{"color": "Blue", "depth": 2}]},
            "2": {"capacity": 2, "layers": []},
        }

        normalized = normalize_puzzle(puzzle)

        self.assertTrue(is_completed_bottle(normalized["1"]))
        self.assertEqual(possible_pours(normalized), [])

    def test_load_puzzle_accepts_a_file_path(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "puzzle.json"
            path.write_text('{"1":{"capacity":1,"layers":[{"color":"Red","depth":1}]}}')

            self.assertEqual(
                load_puzzle(str(path)),
                {"1": {"capacity": 1, "layers": [{"color": "Red", "depth": 1}]}},
            )

    def test_normalize_puzzle_accepts_layer_depth_objects(self):
        puzzle = {
            "1": {
                "capacity": 4,
                "layers": [
                    {"color": "Red", "depth": 2},
                    {"color": "Red", "depth": 1},
                ],
            },
            "2": {"capacity": 4, "layers": []},
        }

        normalized = normalize_puzzle(puzzle)

        self.assertEqual(normalized["1"].layers, (Layer("Red", 3),))

    def test_normalize_puzzle_rejects_string_layers(self):
        puzzle = {
            "1": {"capacity": 4, "layers": ["Red"]},
            "2": {"capacity": 4, "layers": []},
        }

        with self.assertRaisesRegex(ValueError, "Each layer must be an object"):
            normalize_puzzle(puzzle)

    def test_apply_pour_returns_a_new_puzzle(self):
        puzzle = {
            "1": {
                "capacity": 2,
                "layers": [
                    {"color": "Blue", "depth": 1},
                    {"color": "Red", "depth": 1},
                ],
            },
            "2": {"capacity": 2, "layers": [{"color": "Red", "depth": 1}]},
        }

        normalized = normalize_puzzle(puzzle)
        next_puzzle = apply_pour(normalized, ("1", "2"))

        self.assertEqual(
            puzzle["1"]["layers"],
            [
                {"color": "Blue", "depth": 1},
                {"color": "Red", "depth": 1},
            ],
        )
        self.assertEqual(normalized["1"].layers, (Layer("Blue"), Layer("Red")))
        self.assertEqual(next_puzzle["1"].layers, (Layer("Blue"),))
        self.assertEqual(next_puzzle["2"].layers, (Layer("Red", 2),))

    def test_pour_can_move_part_of_a_deep_layer(self):
        puzzle = {
            "1": {"capacity": 4, "layers": [{"color": "Red", "depth": 3}]},
            "2": {"capacity": 4, "layers": [{"color": "Red", "depth": 2}]},
        }

        next_puzzle = apply_pour(normalize_puzzle(puzzle), ("1", "2"))

        self.assertEqual(next_puzzle["1"].layers, (Layer("Red"),))
        self.assertEqual(next_puzzle["2"].layers, (Layer("Red", 4),))

    def test_puzzle_key_includes_layer_depths(self):
        first = normalize_puzzle({
            "1": {"capacity": 4, "layers": [{"color": "Red", "depth": 2}]},
            "2": {"capacity": 4, "layers": []},
        })
        second = normalize_puzzle({
            "1": {"capacity": 4, "layers": [{"color": "Red", "depth": 1}]},
            "2": {"capacity": 4, "layers": []},
        })

        self.assertNotEqual(puzzle_key(first), puzzle_key(second))

    def test_puzzle_key_treats_empty_bottles_as_equivalent(self):
        first = normalize_puzzle({
            "1": {"capacity": 4, "layers": [{"color": "Red", "depth": 1}]},
            "2": {"capacity": 4, "layers": []},
            "3": {"capacity": 4, "layers": []},
        })
        second = normalize_puzzle({
            "1": {"capacity": 4, "layers": []},
            "2": {"capacity": 4, "layers": [{"color": "Red", "depth": 1}]},
            "3": {"capacity": 4, "layers": []},
        })

        self.assertEqual(puzzle_key(first), puzzle_key(second))

    def test_string_bottle_ids_are_valid(self):
        puzzle = {
            "a": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
            "b": {"capacity": 4, "layers": [{"color": "White", "depth": 2}]},
        }

        self.assertEqual(solve_puzzle(puzzle), [("a", "b")])
        self.assertEqual(solve_puzzle_recursive(puzzle), [("a", "b")])

    def test_solve_puzzle_can_log_frontier_growth(self):
        puzzle = {
            "1": {
                "capacity": 2,
                "layers": [
                    {"color": "Red", "depth": 1},
                    {"color": "Blue", "depth": 1},
                ],
            },
            "2": {"capacity": 2, "layers": [{"color": "Blue", "depth": 1}]},
            "3": {"capacity": 2, "layers": [{"color": "Red", "depth": 1}]},
        }
        stream = StringIO()

        solution = solve_puzzle(puzzle, log_progress=True, progress_stream=stream)

        self.assertEqual(solution, [("1", "2"), ("1", "3")])
        self.assertIn("After 1 pours, considering", stream.getvalue())
        self.assertIn("2-pour potential solutions", stream.getvalue())

    def test_solved_requires_empty_or_full_single_color_bottles(self):
        self.assertTrue(
            is_solved(
                normalize_puzzle({
                    "1": {"capacity": 2, "layers": [{"color": "Red", "depth": 2}]},
                    "2": {"capacity": 2, "layers": []},
                })
            )
        )
        self.assertFalse(
            is_solved(
                normalize_puzzle({
                    "1": {"capacity": 2, "layers": [{"color": "Red", "depth": 1}]},
                    "2": {"capacity": 2, "layers": []},
                })
            )
        )


if __name__ == "__main__":
    unittest.main()
