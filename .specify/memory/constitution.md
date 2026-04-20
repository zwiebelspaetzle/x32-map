<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Modified principles: none renamed
Added sections: Security (new section between Technology Stack and Development Workflow)
Removed sections: none
Changed content:
  - Development Workflow: test file reference updated "white christmas.scn" → "test_scene.scn"
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes required
  - .specify/templates/spec-template.md ✅ no changes required
  - .specify/templates/tasks-template.md ✅ no changes required
Deferred TODOs: none
-->

# x32-map Constitution

## Core Principles

### I. Accuracy First

The routing diagram MUST accurately reflect the source scene file at all times.
Any parsed value that cannot be mapped to a known X32 entity MUST be surfaced
explicitly (e.g., labeled "Src {idx}") rather than silently dropped or
approximated. Correctness of the data model takes precedence over visual polish.

### II. Minimal Dependencies

Scripts MUST use Python standard library only. External packages (pip installs)
are prohibited unless a specific capability is demonstrably unavailable in the
stdlib and the dependency is pinned with a rationale comment. HTML output MUST
be fully self-contained — no CDN links, no external stylesheets or scripts.

### III. CLI-First

Every script MUST be directly executable from the command line with positional
arguments (e.g., `python3 x32_routing.py "scene.scn"`). Scripts MUST write
primary output to stdout or a file argument and errors to stderr. Interactive or
GUI-only entry points are not permitted as the primary interface.

### IV. Single-File Scripts

Each distinct capability MUST live in a single self-contained Python file.
Shared logic is inlined or duplicated rather than extracted into a shared module
unless the duplication exceeds three files. This keeps the tool usable without
installation or packaging.

### V. Output Portability

Generated HTML files MUST open correctly in any modern browser with no server
required (i.e., `file://` protocol, no CORS-sensitive fetches). All assets
(styles, scripts, data) MUST be inlined into the single HTML file.

## Technology Stack

- **Language**: Python 3.9+ (f-strings, pathlib, dataclasses allowed)
- **Dependencies**: Python stdlib only (re, sys, json, pathlib, html, etc.)
- **Output format**: Self-contained HTML with inline CSS and JavaScript
- **Input format**: Behringer X32 `.scn` scene files (text-based key/value format)
- **Platform**: macOS/Linux; Windows compatibility is best-effort

## Security

Scene files are treated as potentially untrusted input and MUST be handled
defensively:

- **HTML escaping**: All string values read from a scene file (channel names,
  labels, etc.) MUST be HTML-escaped before insertion into generated output.
  Use `html.escape()` from the Python stdlib; never interpolate raw scene data
  directly into HTML or JavaScript strings.
- **No code execution**: Parsers MUST NOT use `eval()`, `exec()`, or
  `subprocess` on any data derived from scene file content.
- **No network access**: Scripts MUST NOT make outbound network requests at
  any point during parsing or rendering. Output is always written to local
  files or stdout.
- **Path traversal**: File path arguments MUST be resolved with `Path.resolve()`
  before use. Scripts MUST NOT follow symlinks outside the working directory
  unless the user explicitly provides an absolute path.
- **Input size**: Malformed or unusually large scene files MUST NOT cause
  unbounded memory use; parsing MUST be line-by-line and terminate cleanly on
  malformed input with a stderr message.

## Development Workflow

- Scripts are run directly: `python3 <script>.py <scene-file>`
- Manual testing against real `.scn` files is the primary validation method
- No build step, no packaging, no virtual environment required
- Changes MUST be verified against `test_scene.scn` before commit
- New decode functions MUST handle unknown indices gracefully (return a
  labeled fallback, never raise an unhandled exception)

## Governance

This constitution supersedes all informal conventions. Amendments require:
1. A clear rationale documenting what changed and why.
2. A version bump following semantic versioning (MAJOR for principle removal/
   redefinition, MINOR for additions, PATCH for clarifications).
3. Review of all `.specify/templates/` files for alignment after any MAJOR
   or MINOR bump.

All feature specs and implementation plans MUST include a Constitution Check
section verifying compliance with Principles I–V and the Security section
before work begins.

**Version**: 1.1.0 | **Ratified**: 2026-04-20 | **Last Amended**: 2026-04-20
