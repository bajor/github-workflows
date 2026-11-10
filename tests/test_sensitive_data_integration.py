"""Integration coverage for the actual PII workflow shell steps."""

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/secret-scanning.yml"


class SensitiveDataIntegrationTest(unittest.TestCase):
    def scan(self, *, step_name, content, flag):
        step = WORKFLOW.read_text().split(f"      - name: {step_name}\n", maxsplit=1)[1]
        script = textwrap.dedent(text=step.split("        run: |\n", maxsplit=1)[1]
                                 .split("\n      - name:", maxsplit=1)[0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fixture.md").write_text(data=content)
            state = root / "state"
            state.touch()
            result = subprocess.run(
                args=["bash", "-eo", "pipefail", "-c", script],
                cwd=root, env=dict(os.environ, GITHUB_ENV=str(state)),
                capture_output=True, text=True, check=True,
            )
            return f"{flag}=true" in state.read_text(), result.stdout

    def test_email_exception_is_limited_to_the_ssh_host(self):
        at = "@"
        allowed = f"git{at}github.com"
        other = f"other{at}github.com"
        cases = (
            (f"{allowed}:bajor/repo.git", False),
            (f"{allowed} {allowed}", False),
            (other, True),
            (f"{allowed}.evil", True),
            (f"x{allowed}", True),
            (f"{allowed} {other}", True),
        )
        for content, expected in cases:
            with self.subTest(content=content):
                found, output = self.scan(step_name="Scan for email addresses",
                                          content=content, flag="EMAIL_FOUND")
                self.assertEqual(first=found, second=expected, msg=output)

    def test_phone_exception_is_limited_to_the_integer_literal(self):
        allowed = str(object=2**31 - 1)
        other = str(object=2_345_678_901)
        cases = (
            (allowed, False),
            (f"{allowed} {allowed}", False),
            (other, True),
            (f"1{allowed}", True),
            (f"{allowed}8", True),
            (f"{allowed} {other}", True),
        )
        for content, expected in cases:
            with self.subTest(content=content):
                found, output = self.scan(step_name="Scan for phone numbers",
                                          content=content, flag="PHONE_FOUND")
                self.assertEqual(first=found, second=expected, msg=output)


if __name__ == "__main__":
    unittest.main()
