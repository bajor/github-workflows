import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


def phone_step(*, workflow: str) -> str:
    selected = workflow.split('      - name: Scan for phone numbers\n', maxsplit=1)[1]
    body = selected.split('        run: |\n', maxsplit=1)[1]
    return textwrap.dedent(text=body.split('\n      - name:', maxsplit=1)[0])


def scan(*, source: str, script: str) -> bool:
    with tempfile.TemporaryDirectory(prefix='phone-scan-') as temporary:
        root = Path(temporary)
        checkout = root / 'checkout'
        checkout.mkdir()
        checkout.joinpath('payload.json').write_text(data=source, encoding='utf-8')
        output = root / 'environment'
        environment = dict(os.environ, GITHUB_ENV=str(output))
        completed = subprocess.run(args=['bash', '-e', '-o', 'pipefail', '-c', script], cwd=checkout, env=environment, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise AssertionError(completed.stderr)
        return output.exists() and 'PHONE_FOUND=true' in output.read_text()


class PhoneScannerTests(unittest.TestCase):
    def test_hash_substrings_do_not_count_as_phone_numbers(self):
        workflow = Path('.github/workflows/secret-scanning.yml').read_text()
        script = phone_step(workflow=workflow)
        samples = ['bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e',
                   'a' + '2468675309' + 'b' * 53, '2' * 64]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertFalse(expr=scan(source='{"sha256":"' + sample + '"}', script=script))

    def test_recognized_phone_formats_still_fail_including_beside_a_hash(self):
        script = phone_step(workflow=Path('.github/workflows/secret-scanning.yml').read_text())
        for number in ['2468675309', '246-867-5309', '(246) 867-5309', '+1 246 867 5309']:
            with self.subTest(number=number):
                source = '{"sha256":"' + 'a' * 64 + '","contact":"' + number + '"}'
                self.assertTrue(expr=scan(source=source, script=script))

    def test_previous_expression_reproduces_the_hash_failure(self):
        workflow = Path('.github/workflows/secret-scanning.yml').read_text()
        script = phone_step(workflow=workflow)
        current = r'(^|[^[:alnum:]_])(\+?1?[-.[:space:]]?)?\(?[0-9]{3}\)?[-.[:space:]]?[0-9]{3}[-.[:space:]]?[0-9]{4}([^[:alnum:]_]|$)'
        previous = r'(\+?1?[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        self.assertIn(member=current, container=script)
        broken = script.replace(current, previous)
        sample = '{"sha256":"bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e"}'
        self.assertTrue(expr=scan(source=sample, script=broken))
        self.assertFalse(expr=scan(source=sample, script=script))


if __name__ == '__main__':
    unittest.main()
