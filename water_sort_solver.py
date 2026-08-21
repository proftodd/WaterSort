from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO


BottleId = str
Pour = tuple[BottleId, BottleId]


@dataclass(frozen=True)
class Layer:
    color: str
    depth: int = 1


@dataclass(frozen=True)
class Bottle:
    capacity: int
    layers: tuple[Layer, ...]


Puzzle = dict[BottleId, Bottle]


def total_depth(bottle: Bottle) -> int:
    return sum(layer.depth for layer in bottle.layers)


def is_completed_bottle(bottle: Bottle) -> bool:
    return (
        len(bottle.layers) == 1
        and bottle.layers[0].depth == bottle.capacity
    )


def normalize_layers(raw_layers: Sequence[Any]) -> tuple[Layer, ...]:
    layers: list[Layer] = []

    for raw_layer in raw_layers:
        if not isinstance(raw_layer, Mapping):
            raise ValueError("Each layer must be an object with color and depth.")

        color = str(raw_layer["color"])
        depth = int(raw_layer["depth"])

        if depth < 1:
            raise ValueError("Layer depth must be 1 or higher.")

        if layers and layers[-1].color == color:
            previous = layers[-1]
            layers[-1] = Layer(previous.color, previous.depth + depth)
        else:
            layers.append(Layer(color, depth))

    return tuple(layers)


def normalize_puzzle(raw_puzzle: Mapping[Any, Mapping[str, Any]]) -> Puzzle:
    """Convert the input shape into immutable bottle/layer values."""
    puzzle: Puzzle = {}

    for raw_number, raw_bottle in raw_puzzle.items():
        number = str(raw_number)
        capacity = int(raw_bottle["capacity"])
        layers = normalize_layers(raw_bottle["layers"])

        if capacity < 0:
            raise ValueError(f"Bottle {number} has a negative capacity.")
        if sum(layer.depth for layer in layers) > capacity:
            raise ValueError(f"Bottle {number} has more layers than its capacity.")

        puzzle[number] = Bottle(capacity=capacity, layers=layers)

    return puzzle


def is_solved(puzzle: Puzzle) -> bool:
    return all(
        not bottle.layers
        or is_completed_bottle(bottle)
        for bottle in puzzle.values()
    )


def is_valid_pour(
    puzzle: Puzzle,
    pour: Pour,
) -> bool:
    source_number, destination_number = pour

    if source_number == destination_number:
        return False

    source = puzzle[source_number]
    destination = puzzle[destination_number]

    if not source.layers:
        return False
    if is_completed_bottle(source):
        return False
    if total_depth(destination) >= destination.capacity:
        return False
    if not destination.layers:
        return len(source.layers) > 1

    return source.layers[-1].color == destination.layers[-1].color


def possible_pours(puzzle: Puzzle) -> list[Pour]:
    bottle_numbers = list(puzzle)

    return [
        (source_number, destination_number)
        for source_number in bottle_numbers
        for destination_number in bottle_numbers
        if is_valid_pour(
            puzzle,
            (source_number, destination_number),
        )
    ]


def apply_pour(puzzle: Puzzle, pour: Pour) -> Puzzle:
    source_number, destination_number = pour
    source = puzzle[source_number]
    destination = puzzle[destination_number]
    source_top = source.layers[-1]
    pour_depth = min(source_top.depth, destination.capacity - total_depth(destination))
    moving_layer = Layer(source_top.color, pour_depth)

    if source_top.depth == pour_depth:
        source_layers = source.layers[:-1]
    else:
        source_layers = (*source.layers[:-1], Layer(source_top.color, source_top.depth - pour_depth))

    if destination.layers and destination.layers[-1].color == moving_layer.color:
        destination_top = destination.layers[-1]
        destination_layers = (
            *destination.layers[:-1],
            Layer(destination_top.color, destination_top.depth + moving_layer.depth),
        )
    else:
        destination_layers = (*destination.layers, moving_layer)

    return {
        number: (
            Bottle(source.capacity, source_layers)
            if number == source_number
            else Bottle(destination.capacity, destination_layers)
            if number == destination_number
            else Bottle(bottle.capacity, bottle.layers)
        )
        for number, bottle in puzzle.items()
    }


BottleState = tuple[int, tuple[tuple[str, int], ...]]


def bottle_key(bottle: Bottle) -> BottleState:
    return (
        bottle.capacity,
        tuple((layer.color, layer.depth) for layer in bottle.layers),
    )


def puzzle_key(puzzle: Puzzle) -> tuple[BottleState, ...]:
    return tuple(sorted(bottle_key(bottle) for bottle in puzzle.values()))


def solve_puzzle(
    raw_puzzle: Mapping[Any, Mapping[str, Any]],
    *,
    log_progress: bool = False,
    progress_stream: TextIO | None = None,
) -> list[Pour] | None:
    puzzle = normalize_puzzle(raw_puzzle)
    visited = {puzzle_key(puzzle)}
    queue: deque[tuple[Puzzle, tuple[Pour, ...]]] = deque([(puzzle, ())])
    current_depth = 0

    def log(message: str) -> None:
        if log_progress:
            print(message, file=progress_stream or sys.stderr, flush=True)

    while queue:
        paths_at_current_depth = len(queue)
        next_depth_paths = 0

        for _ in range(paths_at_current_depth):
            current_puzzle, path = queue.popleft()
            if is_solved(current_puzzle):
                log(f"Solution found after {len(path)} pours.")
                return list(path)

            pours = possible_pours(current_puzzle)
            for pour in pours:
                next_puzzle = apply_pour(current_puzzle, pour)
                next_key = puzzle_key(next_puzzle)
                if next_key in visited:
                    continue

                visited.add(next_key)
                queue.append((next_puzzle, (*path, pour)))
                next_depth_paths += 1

        if current_depth > 0:
            log(
                f"After {current_depth} pours, considering "
                f"{next_depth_paths} {current_depth + 1}-pour potential solutions "
                f"({len(visited)} unique states seen)."
            )
        current_depth += 1

    return None


def solve_puzzle_recursive(raw_puzzle: Mapping[Any, Mapping[str, Any]]) -> list[Pour] | None:
    puzzle = normalize_puzzle(raw_puzzle)
    visited = {puzzle_key(puzzle)}

    def search(current_puzzle: Puzzle) -> tuple[bool, list[Pour]]:
        if is_solved(current_puzzle):
            return True, []

        pours = possible_pours(current_puzzle)
        if not pours:
            return False, []

        for pour in pours:
            next_puzzle = apply_pour(current_puzzle, pour)
            next_key = puzzle_key(next_puzzle)
            if next_key in visited:
                continue

            visited.add(next_key)
            solved, solution = search(next_puzzle)
            if solved:
                return True, [pour, *solution]

        return False, []

    solved, solution = search(puzzle)
    return solution if solved else None


def solve_all_puzzles(raw_puzzle: Mapping[Any, Mapping[str, Any]]) -> list[list[Pour]]:
    puzzle = normalize_puzzle(raw_puzzle)
    solutions: list[list[Pour]] = []
    stack: list[tuple[Puzzle, list[Pour]]] = [(puzzle, [])]

    while stack:
        current_puzzle, path = stack.pop()
        if is_solved(current_puzzle):
            solutions.append(path)
            continue

        pours = possible_pours(current_puzzle)
        for pour in reversed(pours):
            next_puzzle = apply_pour(current_puzzle, pour)
            stack.append((next_puzzle, [*path, pour]))

    return solutions


def load_puzzle(argument: str) -> Mapping[Any, Mapping[str, Any]]:
    path = Path(argument)
    text = path.read_text() if path.is_file() else argument

    return json.loads(text)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Solve a Water Sort puzzle.")
    parser.add_argument("puzzle", help="JSON object or path to a JSON puzzle file.")
    parser.add_argument(
        "--log-progress",
        action="store_true",
        help="Log BFS frontier sizes to stderr as each pour depth is expanded.",
    )
    parser.add_argument(
        "--strategy",
        choices=("bfs", "recursive"),
        default="bfs",
        help="Search strategy to use. BFS finds the shortest solution; recursive uses depth-first recursion.",
    )
    args = parser.parse_args(argv)

    try:
        puzzle = load_puzzle(args.puzzle)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 2

    try:
        if args.strategy == "recursive":
            solution = solve_puzzle_recursive(puzzle)
        else:
            solution = solve_puzzle(
                puzzle,
                log_progress=args.log_progress,
                progress_stream=sys.stderr,
            )
    except ValueError as error:
        print(f"Invalid puzzle: {error}", file=sys.stderr)
        return 2
    except RecursionError:
        print("Search exceeded Python's recursion limit before finding a solution.", file=sys.stderr)
        return 3

    if solution is None:
        print("No solution found.")
        return 1

    print(json.dumps(solution))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
