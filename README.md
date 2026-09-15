# crush-analyze

A sibling CLI tool for [Crush](https://github.com/kalink0/crush-forensics)
that runs small, curated artifact-parsing modules and reports the result as
a versioned JSON contract Crush reads back into a table view — without
pulling a whole external forensic suite into Crush's own process.

A module is just a `run(context) -> ModuleResult` function plus a small
`ModuleInfo` descriptor (see `crush_analyze/modules/base.py`); the first
modules are ported from LEAPP (iLEAPP/aLEAPP/rLEAPP) artifact scripts, but
the interface itself isn't LEAPP-specific — anything that can turn a
directory of files into typed columns and rows fits the same contract.

See [`docs/design/analyzer-runner.md`](https://github.com/kalink0/crush-forensics/blob/main/docs/design/analyzer-runner.md)
in crush-forensics for the full design: motivation, the frozen result
contract v1, the vendoring policy, and the module-update mechanism.

## CLI

```sh
crush-analyze list-modules
crush-analyze run --module <id> --input <dir> --output <file>.json
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
