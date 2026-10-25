#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from water_sort_solver import solve_puzzle, solve_puzzle_recursive


Color = tuple[int, int, int]


@dataclass(frozen=True)
class BottleBox:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    @property
    def center_x(self) -> int:
        return (self.left + self.right) // 2

    @property
    def center_y(self) -> int:
        return (self.top + self.bottom) // 2


def import_pillow() -> tuple[Any, Any, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as error:
        raise SystemExit(
            "Pillow is required. Create a venv and run: "
            "python -m pip install -r requirements.txt"
        ) from error

    return Image, ImageDraw, ImageFont


def is_outline_pixel(color: Color) -> bool:
    red, green, blue = color
    return (
        145 <= red <= 235
        and 145 <= green <= 235
        and 145 <= blue <= 235
        and max(color) - min(color) <= 35
    )


def find_components(mask: bytearray, width: int, height: int) -> list[tuple[int, BottleBox]]:
    visited = bytearray(width * height)
    components: list[tuple[int, BottleBox]] = []

    for start in range(width * height):
        if not mask[start] or visited[start]:
            continue

        stack = [start]
        visited[start] = 1
        count = 0
        min_x = max_x = start % width
        min_y = max_y = start // width

        while stack:
            index = stack.pop()
            count += 1
            x = index % width
            y = index // width
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            for neighbor in (
                index - 1 if x > 0 else -1,
                index + 1 if x < width - 1 else -1,
                index - width if y > 0 else -1,
                index + width if y < height - 1 else -1,
            ):
                if neighbor >= 0 and mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)

        components.append((count, BottleBox(min_x, min_y, max_x, max_y)))

    return components


def detect_bottle_boxes(image: Any) -> list[BottleBox]:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    pixels = rgb_image.load()
    mask = bytearray(width * height)
    min_y = int(height * 0.27)

    for y in range(min_y, height):
        row = y * width
        for x in range(width):
            if is_outline_pixel(pixels[x, y]):
                mask[row + x] = 1

    components = find_components(mask, width, height)
    boxes = [
        box
        for count, box in components
        if count >= 900
        and 80 <= box.width <= 190
        and 350 <= box.height <= 700
    ]

    if not boxes:
        raise ValueError("No bottle outlines found.")

    return sort_boxes_row_major(boxes)


def sort_boxes_row_major(boxes: Sequence[BottleBox]) -> list[BottleBox]:
    sorted_boxes = sorted(boxes, key=lambda box: box.center_y)
    rows: list[list[BottleBox]] = []

    for box in sorted_boxes:
        for row in rows:
            row_center = sum(item.center_y for item in row) / len(row)
            if abs(box.center_y - row_center) < max(80, box.height * 0.25):
                row.append(box)
                break
        else:
            rows.append([box])

    rows.sort(key=lambda row: sum(box.center_y for box in row) / len(row))
    return [
        box
        for row in rows
        for box in sorted(row, key=lambda item: item.center_x)
    ]


def average_color(image: Any, center_x: int, center_y: int, radius: int = 8) -> Color:
    pixels = image.load()
    width, height = image.size
    totals = [0, 0, 0]
    count = 0

    for y in range(max(0, center_y - radius), min(height, center_y + radius + 1)):
        for x in range(max(0, center_x - radius), min(width, center_x + radius + 1)):
            red, green, blue = pixels[x, y]
            totals[0] += red
            totals[1] += green
            totals[2] += blue
            count += 1

    return tuple(round(total / count) for total in totals)  # type: ignore[return-value]


def color_distance(first: Color, second: Color) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(first, second)))


def hex_color(color: Color) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


def is_empty_sample(color: Color) -> bool:
    return max(color) < 80


def nearest_color_label(
    color: Color,
    clusters: list[tuple[str, Color, int]],
    threshold: float,
) -> str:
    if clusters:
        label, center, count = min(clusters, key=lambda cluster: color_distance(color, cluster[1]))
        if color_distance(color, center) <= threshold:
            new_count = count + 1
            new_center = tuple(
                round((center[index] * count + color[index]) / new_count)
                for index in range(3)
            )
            clusters[clusters.index((label, center, count))] = (label, new_center, new_count)
            return label

    label = f"color_{len(clusters) + 1:02d}"
    clusters.append((label, color, 1))
    return label


def sample_bottle_layers(
    image: Any,
    box: BottleBox,
    capacity: int,
    clusters: list[tuple[str, Color, int]],
    color_threshold: float,
) -> list[str | None]:
    content_top = box.top + round(box.height * 0.15)
    content_bottom = box.bottom - round(box.height * 0.05)
    slot_height = (content_bottom - content_top) / capacity
    center_x = box.center_x
    slots_bottom_to_top: list[str | None] = []

    for slot in range(capacity):
        sample_y = round(content_bottom - (slot + 0.5) * slot_height)
        color = average_color(image, center_x, sample_y)
        if is_empty_sample(color):
            slots_bottom_to_top.append(None)
        else:
            slots_bottom_to_top.append(nearest_color_label(color, clusters, color_threshold))

    return slots_bottom_to_top


def compress_layers(slots_bottom_to_top: Sequence[str | None]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []

    for color in slots_bottom_to_top:
        if color is None:
            continue
        if layers and layers[-1]["color"] == color:
            layers[-1]["depth"] += 1
        else:
            layers.append({"color": color, "depth": 1})

    return layers


def parse_screenshot(
    image_source: Path | BinaryIO,
    *,
    capacity: int = 4,
    color_threshold: float = 55.0,
) -> tuple[dict[str, Any], list[BottleBox], dict[str, str]]:
    Image, _, _ = import_pillow()
    with Image.open(image_source) as source:
        image = source.convert("RGB")
    boxes = detect_bottle_boxes(image)
    clusters: list[tuple[str, Color, int]] = []
    puzzle: dict[str, Any] = {}

    for index, box in enumerate(boxes, start=1):
        slots = sample_bottle_layers(image, box, capacity, clusters, color_threshold)
        puzzle[str(index)] = {
            "capacity": capacity,
            "layers": compress_layers(slots),
        }

    swatches = {label: hex_color(center) for label, center, _ in clusters}
    return puzzle, boxes, swatches


def annotate_image(image_source: Path | BinaryIO, boxes: Sequence[BottleBox]) -> Any:
    Image, ImageDraw, ImageFont = import_pillow()
    with Image.open(image_source) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)

    for font_name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            font = ImageFont.truetype(font_name, 44)
            break
        except OSError:
            continue
    else:
        font = ImageFont.load_default()

    for index, box in enumerate(boxes, start=1):
        label = str(index)
        draw.rectangle((box.left, box.top, box.right, box.bottom), outline=(255, 255, 255), width=4)
        draw.text(
            (box.center_x, box.top + 30),
            label,
            fill=(255, 255, 255),
            anchor="mm",
            font=font,
            stroke_width=3,
            stroke_fill=(0, 0, 0),
        )

    return image


def save_annotated_image(image_path: Path, boxes: Sequence[BottleBox], output_path: Path) -> None:
    annotate_image(image_path, boxes).save(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a Water Sort screenshot.")
    parser.add_argument("image", type=Path, help="Screenshot image path.")
    parser.add_argument("--capacity", type=int, default=4, help="Bottle capacity.")
    parser.add_argument("--annotate", type=Path, help="Write an annotated image with bottle numbers.")
    parser.add_argument("--output", type=Path, help="Write JSON result to this path instead of stdout.")
    parser.add_argument("--solve", action="store_true", help="Include a solution in the output.")
    parser.add_argument(
        "--strategy",
        choices=("bfs", "recursive"),
        default="bfs",
        help="Solver strategy when --solve is used.",
    )
    parser.add_argument(
        "--color-threshold",
        type=float,
        default=55.0,
        help="RGB distance threshold for clustering sampled colors.",
    )
    args = parser.parse_args()

    try:
        puzzle, boxes, swatches = parse_screenshot(
            args.image,
            capacity=args.capacity,
            color_threshold=args.color_threshold,
        )
        if args.annotate:
            save_annotated_image(args.image, boxes, args.annotate)

        result: dict[str, Any] = {
            "puzzle": puzzle,
            "swatches": swatches,
            "bottle_count": len(boxes),
        }
        if args.annotate:
            result["annotated_image"] = str(args.annotate)
        if args.solve:
            solution = (
                solve_puzzle_recursive(puzzle)
                if args.strategy == "recursive"
                else solve_puzzle(puzzle)
            )
            result["strategy"] = args.strategy
            result["solution"] = solution
            result["pours"] = len(solution) if solution is not None else None

    except ValueError as error:
        print(f"Could not parse screenshot: {error}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + "\n")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
