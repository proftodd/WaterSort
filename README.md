# Water Sort Solver

## Setup

Use a project-local virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m unittest -v
```

## Screenshot Parser

Parse a screenshot into puzzle JSON:

```bash
python water_sort_from_image.py IMG_1390.jpeg --annotate IMG_1390_annotated.png
```

Parse and solve in one step:

```bash
python water_sort_from_image.py IMG_1390.jpeg --solve --annotate IMG_1390_annotated.png
```

The parser numbers bottles row-major: top row left-to-right, then the next row
left-to-right.
