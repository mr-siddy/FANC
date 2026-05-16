# Tiny-VM Visualizer

In-browser visualization for the Tiny-VM environment. See `docs/superpowers/specs/2026-05-16-tinyvm-viz-design.md`.

## Develop
- `npm install`
- `npm run dev`
- `npm test`

## Regenerating parity fixtures

After changing the Python interpreter:

```
python -m tinyvm.scripts.export_golden_fixtures
```

then re-run `npm test` in `tinyvm-viz/` and commit `tests/fixtures/golden.json` together with the interpreter change.
