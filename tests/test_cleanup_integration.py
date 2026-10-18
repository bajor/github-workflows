"""Integration tests using real Git repositories, not mocked filesystem units."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / ".github/actions/cleanup-generated/cleanup.py"


class CleanupIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q", "-b", "main")
        self.write("source.py", "do_not_delete = True\n")
        self.write("visual-explanations/nested/review.svg", "<svg/>\n")
        self.write("visual-explanations/keep.txt", "keep\n")
        self.write("raccoon-artifacts/pr-7/manifest.json", "{}\n")
        self.write("raccoon-artifacts/pr-7/files/source.txt", "real source\n")
        self.write("raccoon-artifacts/settings.json", "{}\n")
        self.catalog = {"version": 1, "repository": "bajor/example", "artifacts": [{"pr": 7, "manifest": "pr-7/manifest.json"}]}
        self.write("raccoon-artifacts/catalog.json", json.dumps(self.catalog))
        self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.PIPE)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "Fixture")

    def run_cleanup(self, enabled=False):
        env = dict(os.environ, GITHUB_REPOSITORY="bajor/example", DELETE_RACCOON_ARTIFACTS=str(enabled).lower())
        return subprocess.run(["python3", str(SCRIPT)], cwd=self.root, env=env, capture_output=True, text=True)

    def test_default_preserves_raccoon_material(self):
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "visual-explanations/nested/review.svg").exists())
        self.assertTrue((self.root / "visual-explanations/keep.txt").exists())
        self.assertTrue((self.root / "raccoon-artifacts/pr-7/files/source.txt").exists())

    def test_opt_in_deletes_only_owned_tracked_pr_material(self):
        self.write("raccoon-artifacts/pr-99/not-in-catalog.txt", "preserve unlisted material\n")
        self.commit()
        self.write("raccoon-artifacts/pr-7/personal-note.txt", "untracked, preserve\n")
        result = self.run_cleanup(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "raccoon-artifacts/pr-7/files/source.txt").exists())
        self.assertTrue((self.root / "raccoon-artifacts/pr-7/personal-note.txt").exists())
        self.assertTrue((self.root / "source.py").exists())
        self.assertTrue((self.root / "raccoon-artifacts/settings.json").exists())
        self.assertTrue((self.root / "raccoon-artifacts/pr-99/not-in-catalog.txt").exists())
        self.assertEqual(json.loads((self.root / "raccoon-artifacts/catalog.json").read_text())["artifacts"], [])

    def test_rejects_unowned_catalog_before_deleting_anything(self):
        self.catalog["repository"] = "other/repo"
        self.write("raccoon-artifacts/catalog.json", json.dumps(self.catalog))
        self.commit()
        result = self.run_cleanup(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("status", "--porcelain"), b"")

    def test_rejects_catalog_symlink_without_reading_its_target(self):
        self.write("valid-catalog.json", json.dumps(self.catalog))
        target = self.root / "raccoon-artifacts/catalog.json"
        target.unlink()
        target.symlink_to("../valid-catalog.json")
        self.commit()
        result = self.run_cleanup(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("status", "--porcelain"), b"")

    def test_rejects_symlinked_artifact_root(self):
        self.git("mv", "raccoon-artifacts", "other-artifacts")
        (self.root / "raccoon-artifacts").symlink_to("other-artifacts", target_is_directory=True)
        self.commit()
        result = self.run_cleanup(True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("status", "--porcelain"), b"")

    def test_repeated_cleanup_is_a_noop_after_the_cleanup_commit(self):
        self.assertEqual(self.run_cleanup(True).returncode, 0)
        self.commit()
        result = self.run_cleanup(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), b"")

    def test_missing_generated_directories_are_a_noop(self):
        self.git("rm", "-qr", "visual-explanations", "raccoon-artifacts")
        self.commit()
        result = self.run_cleanup(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("status", "--porcelain"), b"")


if __name__ == "__main__":
    unittest.main()
