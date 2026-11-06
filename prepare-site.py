#!/usr/bin/env python3
"""Build Alienway's Pages artifact without changing its checked-in bundle.

Uses only Python's standard library. A different source bundle must be reviewed
before updating the pinned hashes and the corresponding integration tests.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

SOURCE_BLOB_SHA1 = "178df7e39b13d8b606ba27667f4ddb7cfff1c8d2"
BUILT_SHA256 = "7604f967c69878cfbe6adf30e59e0460a16035722e6090ad5f3c32b22f263e13"
LOADER = b'  <script defer src="/analytics.js" data-measurement-id="G-YT66SSVBMF"></script>\n'
MARKER = b"    window.__alienwayPageReady = true;\n    window.dispatchEvent(new CustomEvent('alienway:page-ready'));\n"
HEAD_ANCHOR = b"  <title>Bundled Page</title>\n"
READY_ANCHOR = b"      window.Babel.transformScriptTags();\n    }\n"
EXCLUDED = {"tests", "docs", "build", "dist", "node_modules", "__pycache__", "_site", "prepare-site.py"}


class BuildError(Exception):
    pass


def blob_sha1(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def inject_analytics(original):
    if blob_sha1(original) != SOURCE_BLOB_SHA1:
        raise BuildError("Source index.html does not match the reviewed baseline; no artifact published")
    if original.count(HEAD_ANCHOR) != 1 or original.count(READY_ANCHOR) != 1:
        raise BuildError("Expected bundle integration points are not unique")
    built = original.replace(HEAD_ANCHOR, HEAD_ANCHOR + LOADER).replace(READY_ANCHOR, READY_ANCHOR + MARKER)
    if hashlib.sha256(built).hexdigest() != BUILT_SHA256:
        raise BuildError("Built index.html differs from the reviewed analytics patch")
    return built


def excluded(name):
    return (name in EXCLUDED or (name.startswith(".") and name not in {".well-known", ".nojekyll"})
            or name.lower().endswith((".md", ".rst")))


def copy_runtime(root, target):
    for directory, subdirs, files in os.walk(root, followlinks=False):
        source_dir = Path(directory)
        subdirs[:] = [name for name in subdirs if not excluded(name)]
        for name in subdirs:
            if (source_dir / name).is_symlink():
                raise BuildError("Runtime symlinks are not supported by the Pages artifact")
        relative = source_dir.relative_to(root)
        (target / relative).mkdir(parents=True, exist_ok=True)
        for name in files:
            if excluded(name):
                continue
            source = source_dir / name
            if source.is_symlink() or not source.is_file():
                raise BuildError("Runtime entries must be regular files")
            # A real copy keeps symbolic and hard links out of the Pages artifact.
            shutil.copyfile(source, target / relative / name)


def build_site(root=None):
    root = Path(root or Path(__file__).resolve().parent).resolve()
    index = root / "index.html"
    analytics = root / "analytics.js"
    output = root / "_site"
    for required in (index, analytics):
        if required.is_symlink() or not required.is_file():
            raise BuildError(f"Required runtime file is missing or not regular: {required.name}")
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise BuildError("_site must be a regular directory")
    original = index.read_bytes()
    built = inject_analytics(original)
    staging = Path(tempfile.mkdtemp(prefix=".site-build-", dir=root))
    backup = None
    try:
        copy_runtime(root, staging)
        (staging / "index.html").write_bytes(built)
        if index.read_bytes() != original:
            raise BuildError("Source bundle changed during the build; no artifact published")
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=".site-backup-", dir=root))
            backup.rmdir()
            output.replace(backup)
        try:
            staging.replace(output)
        except Exception:
            if backup is not None:
                backup.replace(output)
            raise
        if backup is not None:
            shutil.rmtree(backup)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"output": "_site", "source_blob_sha1": blob_sha1(original),
            "built_sha256": hashlib.sha256(built).hexdigest(), "built_bytes": len(built)}


if __name__ == "__main__":
    try:
        print(json.dumps(build_site(), sort_keys=True))
    except (BuildError, OSError) as error:
        raise SystemExit(str(error)) from None
