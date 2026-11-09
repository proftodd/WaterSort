# Azure Functions

The project includes a Python v2 Azure Functions app in `function_app.py`.
It calls the same parser and solver as the standalone HTTP server. Images
and annotated responses stay in memory; no shared filesystem or custom
container is required.

## Local Setup

Use Azure Functions Core Tools v4 and Python 3.13. The existing `.venv` can
remain the interpreter for the standalone server in PyCharm. A separate
environment keeps Azure testing on the same Python version as deployment:

```bash
python3.13 -m venv .venv-azure
source .venv-azure/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
```

On macOS, install or upgrade the Functions tools with Homebrew:

```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
brew link --overwrite azure-functions-core-tools@4
func --version
```

If version 4 is already installed, use `brew upgrade
azure-functions-core-tools@4`. The `func --version` result must start with
`4.`. Use a current Azure CLI for deployment (`brew upgrade azure-cli` on
macOS). On Linux, follow Microsoft's linked installation instructions.

`local.settings.json` is ignored by Git and deployment. If it is absent,
copy `local.settings.example.json` to `local.settings.json`. Its empty
storage setting is for local HTTP-only development; deployed Functions
use the storage account configured in Azure.

With `.venv-azure` active, run from the project directory:

```bash
func start
```

The endpoints are:

| Method | Local URL | Body |
| --- | --- | --- |
| GET | `http://localhost:7071/api/health` | None |
| POST | `http://localhost:7071/api/solve` | Puzzle JSON |
| POST | `http://localhost:7071/api/solve-image` | Raw image bytes |

For example:

```bash
curl 'http://localhost:7071/api/solve-image?strategy=recursive' \
  -H 'Content-Type: image/jpeg' \
  --data-binary @IMG_1390.jpeg
```

In Bruno, use the same URL and select a file body with the screenshot;
send `Content-Type: image/jpeg` (or `image/png`). Do not use a JSON file
path or multipart form data. The JSON response includes the solution,
detected puzzle, bottle bounds, swatches, and base64-encoded annotated PNG.
Uploads are limited to 20 MiB. The default strategy is `bfs`.

All endpoints require a function key in Azure. Core Tools does not enforce
keys locally by default. Handler unit tests also do not test host-level
authentication.

## Create Azure Resources

These commands create billable resources. They are instructions to run
when ready to deploy, not a setup step needed for local tests.

Sign in and choose the intended subscription:

```bash
az login
az account list -o table
az account set --subscription 'YOUR-SUBSCRIPTION-ID'
```

Pick globally unique names for the Function App and storage account.
Storage names must have 3-24 lowercase letters or digits. For example:

```bash
WATER_SORT_GROUP='water-sort-rg'
WATER_SORT_REGION='eastus2'
WATER_SORT_APP="john-water-sort-$(date +%s)"
WATER_SORT_STORAGE="watersort$(date +%s)"
```

Check regional availability and change `WATER_SORT_REGION` if needed:

```bash
az functionapp list-flexconsumption-locations -o table
```

Create the resource group, storage account, and Flex Consumption app:

```bash
az group create --name "$WATER_SORT_GROUP" --location "$WATER_SORT_REGION"

az storage account create \
  --name "$WATER_SORT_STORAGE" \
  --resource-group "$WATER_SORT_GROUP" \
  --location "$WATER_SORT_REGION" \
  --sku Standard_LRS

az functionapp create \
  --name "$WATER_SORT_APP" \
  --resource-group "$WATER_SORT_GROUP" \
  --storage-account "$WATER_SORT_STORAGE" \
  --flexconsumption-location "$WATER_SORT_REGION" \
  --runtime python \
  --runtime-version 3.13 \
  --functions-version 4 \
  --instance-memory 2048 \
  --https-only true \
  --disable-app-insights true
```

No always-ready instances are requested. Application Insights is disabled
in this minimal setup; enable it later if invocation telemetry is useful.
Storage and applicable network charges are separate from the Functions
free execution allowance, so a zero total bill is not guaranteed.

## Publish and Invoke

From the project directory, with `.venv-azure` active:

```bash
func azure functionapp publish "$WATER_SORT_APP"

az functionapp show \
  --resource-group "$WATER_SORT_GROUP" \
  --name "$WATER_SORT_APP" \
  --query defaultHostName -o tsv
```

Publishing uses a remote Linux build to install `requirements.txt` for
Azure; the Mac virtual environment is not uploaded. `.funcignore` includes
only the six runtime files, excluding screenshots, saved responses,
virtual environments, tests, and local settings. Do not upload local
settings to Azure, since their storage value is only for local testing.

Use the returned hostname as `https://HOSTNAME/api/solve-image`. In the
Azure portal, open the Function App, select the `solve_image` function,
and choose **Get function URL** to obtain a URL with a function-level key.
In Bruno, supply that key in the `x-functions-key` header or use the full
URL containing `?code=...`. Keep the existing image content type and body.
Add `strategy=recursive` as another query parameter if desired.

`host.json` sets a 210-second function execution timeout. Azure's
synchronous HTTP response limit is 230 seconds; this configuration leaves
some margin but does not guarantee every puzzle finishes. A host timeout
can produce a platform error rather than the solver's JSON response. The
usual response codes are 200 for a solution, 404 for no solution, 400 for
invalid JSON, 415 for a wrong image content type, and 422 for invalid input.

## References

- [Python programming model](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Core Tools setup and deployment](https://learn.microsoft.com/en-us/azure/azure-functions/how-to-create-function-azure-cli?pivots=programming-language-python)
- [Flex Consumption setup](https://learn.microsoft.com/en-us/azure/azure-functions/flex-consumption-how-to)
- [HTTP keys](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-http-webhook-trigger#access-key-authorization)
- [Execution timeouts](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale#function-app-timeout-duration)
- [Pricing](https://azure.microsoft.com/en-us/pricing/details/functions/)
