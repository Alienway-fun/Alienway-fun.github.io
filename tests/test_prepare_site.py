"""Artifact equality, source preservation, and fail-closed build checks."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_site", ROOT / "prepare-site.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)
ORIGINAL = (ROOT / "index.html").read_bytes()
ANALYTICS = (ROOT / "analytics.js").read_bytes()
REVIEWED_SHA256 = "7604f967c69878cfbe6adf30e59e0460a16035722e6090ad5f3c32b22f263e13"


class SiteBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "index.html").write_bytes(ORIGINAL)
        (self.root / "analytics.js").write_bytes(ANALYTICS)
        (self.root / "CNAME").write_bytes(b"alienway.fun")

    def test_build_is_the_reviewed_patch_and_source_stays_byte_identical(self):
        self.assertEqual(build.blob_sha1(ORIGINAL), "178df7e39b13d8b606ba27667f4ddb7cfff1c8d2")
        result = build.build_site(self.root)
        artifact = (self.root / "_site/index.html").read_bytes()
        self.assertEqual(hashlib.sha256(artifact).hexdigest(), REVIEWED_SHA256)
        self.assertEqual(artifact.count(build.LOADER), 1)
        self.assertEqual(artifact.count(build.MARKER), 1)
        self.assertEqual(artifact.replace(build.LOADER, b"").replace(build.MARKER, b""), ORIGINAL)
        self.assertEqual((self.root / "index.html").read_bytes(), ORIGINAL)
        self.assertEqual((self.root / "_site/analytics.js").read_bytes(), ANALYTICS)
        self.assertEqual((self.root / "_site/CNAME").read_bytes(), b"alienway.fun")
        self.assertEqual(result["built_sha256"], REVIEWED_SHA256)

    def test_runtime_assets_are_copied_and_development_files_excluded(self):
        for filename in (".git/config", ".github/workflows/site-checks.yml", "tests/spec.mjs", "docs/notes.txt",
                         "build/old.html", "dist/old.html", "node_modules/pkg/index.js", "README.md",
                         "prepare-site.py", "__pycache__/compiled.pyc", ".site-build-old/scratch"):
            target = self.root / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("development")
        (self.root / "assets").mkdir()
        (self.root / "assets/video.bin").write_bytes(b"runtime")
        build.build_site(self.root)
        files = {str(path.relative_to(self.root / "_site")) for path in (self.root / "_site").rglob("*") if path.is_file()}
        self.assertEqual(files, {"index.html", "analytics.js", "CNAME", "assets/video.bin"})

    def test_rebuild_replaces_the_complete_artifact_without_recursing(self):
        build.build_site(self.root)
        (self.root / "_site/stale.txt").write_text("stale")
        build.build_site(self.root)
        self.assertFalse((self.root / "_site/stale.txt").exists())
        self.assertFalse((self.root / "_site/_site").exists())
        self.assertEqual(list(self.root.glob(".site-build-*")), [])
        self.assertEqual(list(self.root.glob(".site-backup-*")), [])

    def test_invalid_baseline_cannot_create_or_replace_an_artifact(self):
        (self.root / "index.html").write_bytes(ORIGINAL + b"\n")
        with self.assertRaises(build.BuildError):
            build.build_site(self.root)
        self.assertFalse((self.root / "_site").exists())
        (self.root / "_site").mkdir()
        (self.root / "_site/previous.txt").write_text("previous complete artifact")
        with self.assertRaises(build.BuildError):
            build.build_site(self.root)
        self.assertEqual([path.name for path in (self.root / "_site").iterdir()], ["previous.txt"])

    def test_missing_loader_and_runtime_symlink_cannot_publish_partial_artifact(self):
        (self.root / "analytics.js").unlink()
        with self.assertRaises(build.BuildError):
            build.build_site(self.root)
        self.assertFalse((self.root / "_site").exists())
        (self.root / "analytics.js").write_bytes(ANALYTICS)
        (self.root / "linked.html").symlink_to(self.root / "index.html")
        with self.assertRaises(build.BuildError):
            build.build_site(self.root)
        self.assertFalse((self.root / "_site").exists())
        self.assertEqual(list(self.root.glob(".site-build-*")), [])

    def test_copy_failure_preserves_existing_complete_artifact(self):
        build.build_site(self.root)
        with patch.object(build.shutil, "copyfile", side_effect=OSError("fixture copy failure")):
            with self.assertRaises(OSError):
                build.build_site(self.root)
        self.assertEqual(hashlib.sha256((self.root / "_site/index.html").read_bytes()).hexdigest(), REVIEWED_SHA256)
        self.assertEqual(list(self.root.glob(".site-build-*")), [])


if __name__ == "__main__":
    unittest.main()
