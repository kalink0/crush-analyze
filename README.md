# crush-analyze

A sibling CLI tool for [Crush](https://github.com/kalink0/crush-forensics)
that runs small, curated artifact-parsing modules — ported one at a time
from LEAPP (iLEAPP/aLEAPP/rLEAPP) artifact scripts — and reports the result
as a versioned JSON contract Crush reads back into a table view.

**Status: skeleton only, no real modules ported yet.** See
[`docs/design/analyzer-runner.md`](https://github.com/kalink0/crush-forensics/blob/main/docs/design/analyzer-runner.md)
in crush-forensics for the full design: motivation, the frozen result
contract v1, dev mode, the vendoring policy, and the module-update
mechanism.

## CLI

```sh
crush-analyze list-modules
crush-analyze run --module <id> --input <dir> --output <file>.json
crush-analyze run --module-path <file.py> --dev --input <dir> --output <file>.json
```

Exit codes: `0` success, `1` the module ran but the result's `status` is
`"error"` (a best-effort JSON is still written), `2` the CLI itself
couldn't run at all (bad args, unknown module, output path not writable —
no JSON written).

## Development

```sh
pip install -e ".[dev]"
pytest
ruff check .
mypy .
```
