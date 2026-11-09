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

## HTTP Server

With the virtual environment active, start the server on your network:

```bash
python water_sort_server.py --host 0.0.0.0 --port 8080
```

Upload the image itself as the request body:

```bash
curl 'http://Eusebius:8080/solve-image?strategy=recursive' \
  -H 'Content-Type: image/jpeg' \
  --data-binary @IMG_1390.jpeg
```

Use `image/png` for a PNG screenshot. The filename is read on the client;
the server receives image bytes and does not need access to that file.
Uploads are limited to 20 MiB. The response includes `strategy`, `solution`,
`pours`, the detected `puzzle`, and color `swatches`. Bottle IDs are strings
numbered left-to-right across each row, starting with the top row.
The default strategy is `bfs`; `recursive` is also available.

The existing `POST /solve` endpoint accepts puzzle JSON, and `GET /health`
checks whether the server is running.

Image responses also include `bottles`, mapping each solution bottle ID to
its pixel `bounds` (`left`, `top`, `right`, `bottom`, inclusive), and
`annotated_image`, containing `media_type: "image/png"` and `data_base64`.
Base64-decode `data_base64` to obtain the numbered screenshot, or display it
in a browser using `data:image/png;base64,` followed by that value as an image
source. The numbers on the image match the IDs in `puzzle` and `solution`.
The image is included even when no solution is found (HTTP 404).

Detection currently targets screenshots like the original example: light
bottle outlines with similar dimensions, equal capacity (4), and evenly
spaced liquid units. The annotations identify detected bottles; they do not
make recognition of arbitrary shapes or mixed capacities reliable. Such
layouts need additional detection and capacity inference before they are
supported.

## Azure Functions

The project also includes an Azure Functions entry point with
`/api/health`, `/api/solve`, and `/api/solve-image` routes. It reuses the
same solver and returns the same annotated-image JSON response.
See [AZURE.md](AZURE.md) for local testing, Flex Consumption deployment,
and calling the deployed app from Bruno with a function key.
