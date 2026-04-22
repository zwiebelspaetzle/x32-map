<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

## Constitution

Always read `.specify/memory/constitution.md` at the start of every session before making any changes.

## Project

x32-map parses Behringer X32 `.scn` scene files and generates a self-contained HTML routing diagram.

**Run:** `python3 x32_map.py <scene.scn>`

## Key Constraints

- Python stdlib only — no pip installs
- Single-file scripts; shared logic is inlined, not extracted
- HTML output must be fully self-contained (no CDN, no external assets)
- All scene file string values must be HTML-escaped before output

## Testing

Run tests with:
```
python3 -m pytest
```

Run tests before committing. A pre-commit hook enforces this automatically.
