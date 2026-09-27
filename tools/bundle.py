"""Make a program one file, the way the hub and the SPIKE app want it.

The hub runs one file per slot and a SPIKE app project is one file, so a
program cannot `from robot import ...` another file in programs/ on its own.
This module fixes that at send time: every top-level

    from NAME import ...

whose NAME is a .py file next to the program is replaced by the contents of
that file. Hub modules (`import motor`, `from hub import port`) are not files
here, so they are left alone. `spike run`, the Run button, `spike usb run`,
`spike bundle` and `llsp3.py import` all go through bundle_source().

`import robot` (without `from`) is refused with a clear message: the bundled
names become plain globals, so `robot.drive_cm` would not exist on the hub.
"""

from __future__ import annotations

import re
from pathlib import Path

_IMPORT = re.compile(r"^(?:from\s+(\w+)\s+import\s+(.+)|import\s+(\w+)(?:\s+as\s+\w+)?)\s*(?:#.*)?$")


class BundleError(RuntimeError):
    """A local import the bundler cannot handle; the message says what to change."""


def bundle_source(path: str | Path) -> tuple[str, list[str]]:
    """Return (source with local modules inlined, names of the modules inlined)."""
    done: list[Path] = []
    text = _bundle(Path(path).resolve(), [], done)
    return text, [p.stem for p in done]


def _bundle(path: Path, stack: list[Path], done: list[Path]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _IMPORT.match(line)
        if not m:
            out.append(line)
            i += 1
            continue
        name = m.group(1) or m.group(3)
        module = path.parent / f"{name}.py"
        if not module.is_file():
            out.append(line)  # a hub module, not a file here
            i += 1
            continue
        # A local module. Swallow a parenthesised import's continuation lines:
        #     from robot import (drive_cm,
        #                        turn_degrees)
        if m.group(2) is not None and m.group(2).lstrip().startswith("(") and ")" not in m.group(2):
            while i + 1 < len(lines) and ")" not in lines[i]:
                i += 1
        i += 1
        if m.group(3):
            raise BundleError(
                f"{path.name}: write `from {name} import ...` instead of `import {name}`. "
                f"{name}.py is copied into the program when it is sent to the hub, so its "
                f"functions are used by their plain names (drive_cm, not {name}.drive_cm)."
            )
        module = module.resolve()
        if module in stack or module == path:
            chain = " -> ".join(p.name for p in stack + [path, module])
            raise BundleError(f"circular import: {chain}")
        if module in done:
            out.append(f"# ({name}.py is already included above)")
            continue
        done.append(module)
        body = _bundle(module, stack + [path], done)
        out.append(f"# ---- {name}.py starts here (copied in by spike; edit programs/{name}.py, not this) ----")
        out.append(body.rstrip("\n"))
        out.append(f"# ---- {name}.py ends here ----")
    return "\n".join(out) + "\n"
