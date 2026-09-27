"""Move Python source between SPIKE App 3 project files (.llsp3) and plain .py files.

A .llsp3 project is a ZIP archive holding

    manifest.json     project metadata, "type": "python"
    projectbody.json  {"main": "<the python source>"}
    icon.svg          thumbnail shown in the app

so the same code can live as a normal .py file in VS Code and as a project in
the SPIKE app.

    py tools/llsp3.py export  projects/MyRun.llsp3            -> programs/MyRun.py
    py tools/llsp3.py export  projects/*.llsp3 -o programs
    py tools/llsp3.py import  programs/MyRun.py               -> projects/MyRun.llsp3
    py tools/llsp3.py list    projects/MyRun.llsp3
"""

import argparse
import glob
import json
import os
import random
import shutil
import string
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PY_DIR = os.path.join(ROOT, "programs")
DEFAULT_PROJECT_DIR = os.path.join(ROOT, "projects")

ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">'
    '<rect width="80" height="80" rx="12" fill="#F5F5F5"/>'
    '<text x="40" y="50" font-family="Arial" font-size="28" text-anchor="middle" fill="#4C97FF">py</text>'
    "</svg>"
)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_id():
    alphabet = string.ascii_letters + string.digits
    return "_" + "".join(random.choice(alphabet) for _ in range(11))


def _new_manifest(name, slot=0):
    return {
        "type": "python",
        "appType": "llsp3",
        "autoDelete": False,
        "created": _now(),
        "id": _new_id(),
        "lastsaved": _now(),
        "size": 0,
        "name": name,
        "slotIndex": slot,
        "workspaceX": 120,
        "workspaceY": 120,
        "zoomLevel": 0.5,
        "hardware": {"python": {"type": "flipper"}},
        "state": {},
        "extraFiles": [],
    }


def read_source(path):
    """Return the Python source embedded in a .llsp3 project."""
    with zipfile.ZipFile(path) as zf:
        body = json.loads(zf.read("projectbody.json").decode("utf-8"))
    if "main" not in body:
        raise SystemExit(f"{path}: not a Python project (no 'main' in projectbody.json)")
    return body["main"]


def read_manifest(path):
    with zipfile.ZipFile(path) as zf:
        return json.loads(zf.read("manifest.json").decode("utf-8"))


def write_source(path, source, slot=None):
    """Write `source` into a .llsp3, creating it if it does not exist yet.

    Everything else in the archive (manifest, icon, monitors) is kept as it was.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    if os.path.exists(path):
        with zipfile.ZipFile(path) as zf:
            entries = [(i, zf.read(i.filename)) for i in zf.infolist()]
    else:
        entries = [
            (zipfile.ZipInfo("manifest.json"), b"{}"),
            (zipfile.ZipInfo("icon.svg"), ICON_SVG.encode("utf-8")),
            (zipfile.ZipInfo("projectbody.json"), b"{}"),
        ]

    out = []
    for info, data in entries:
        if info.filename == "projectbody.json":
            body = json.loads(data.decode("utf-8") or "{}")
            body["main"] = source
            data = json.dumps(body).encode("utf-8")
        elif info.filename == "manifest.json":
            manifest = json.loads(data.decode("utf-8") or "{}")
            if not manifest:
                manifest = _new_manifest(name, slot or 0)
            manifest["name"] = name
            manifest["lastsaved"] = _now()
            if slot is not None:
                manifest["slotIndex"] = slot
            data = json.dumps(manifest).encode("utf-8")
        out.append((info.filename, data))

    # Write to a temp file first so a failure never destroys an existing project.
    fd, tmp = tempfile.mkstemp(suffix=".llsp3", dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, data in out:
                zf.writestr(filename, data)
        shutil.move(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def cmd_export(args):
    targets = []
    for pattern in args.files:
        targets.extend(glob.glob(pattern) or [pattern])
    if not targets:
        raise SystemExit("nothing to export")

    for src in targets:
        source = read_source(src)
        if args.out and not os.path.isdir(args.out) and len(targets) == 1:
            dest = args.out
        else:
            out_dir = args.out or DEFAULT_PY_DIR
            os.makedirs(out_dir, exist_ok=True)
            dest = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + ".py")
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(source)
        print(f"{src} -> {dest}")


def cmd_import(args):
    targets = []
    for pattern in args.files:
        targets.extend(glob.glob(pattern) or [pattern])
    if not targets:
        raise SystemExit("nothing to import")

    for src in targets:
        with open(src, encoding="utf-8") as fh:
            source = fh.read()
        if args.out and not os.path.isdir(args.out) and len(targets) == 1:
            dest = args.out
        else:
            out_dir = args.out or DEFAULT_PROJECT_DIR
            os.makedirs(out_dir, exist_ok=True)
            dest = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + ".llsp3")
        existed = os.path.exists(dest)
        write_source(dest, source, args.slot)
        print(f"{src} -> {dest}" + ("" if existed else " (new project)"))


def cmd_list(args):
    for pattern in args.files:
        for path in glob.glob(pattern) or [pattern]:
            manifest = read_manifest(path)
            source = read_source(path)
            print(f"{path}")
            print(f"  name       {manifest.get('name')}")
            print(f"  slotIndex  {manifest.get('slotIndex')}")
            print(f"  lastsaved  {manifest.get('lastsaved')}")
            print(f"  source     {len(source.splitlines())} lines")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("export", help="pull the Python source out of .llsp3 projects")
    p.add_argument("files", nargs="+", help=".llsp3 files (globs allowed)")
    p.add_argument("-o", "--out", help="output file or directory (default: programs/)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("import", help="push .py source into .llsp3 projects")
    p.add_argument("files", nargs="+", help=".py files (globs allowed)")
    p.add_argument("-o", "--out", help="output file or directory (default: projects/)")
    p.add_argument("--slot", type=int, help="slotIndex to record in the manifest")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("list", help="show what is inside .llsp3 projects")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
