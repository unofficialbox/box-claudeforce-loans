"""The Demo Setup card connector stays a bindings-only card and the skill knows how to use it."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / 'connectors' / 'demo-setup-card'
WRITE_VERBS = re.compile(r'\b(apply|approve|generate|sign|send)\b', re.I)


class DemoSetupCardTests(unittest.TestCase):
    def test_connector_package_defines_build_and_test(self):
        package = json.loads((CARD / 'package.json').read_text())
        self.assertEqual(package['type'], 'module')
        for script in ('build', 'test', 'start', 'start:http'):
            self.assertIn(script, package['scripts'])
        self.assertIn('@modelcontextprotocol/ext-apps', package['dependencies'])

    def test_card_offers_no_write_as_a_button(self):
        html = (CARD / 'mcp-app.html').read_text()
        for label in re.findall(r'<button[^>]*>(.*?)</button>', html, re.S):
            self.assertIsNone(WRITE_VERBS.search(label), label)
        self.assertIn('Loan ID and folder come from the live record', html)

    def test_server_marks_confirmation_tool_app_only(self):
        source = (CARD / 'src' / 'server.ts').read_text()
        self.assertIn('"confirmDemoSetup"', source)
        self.assertIn('visibility: ["app"]', source)
        self.assertIn('visibility: ["model", "app"]', source)
        self.assertIn('ui://los-demo-setup/card.html', source)

    def test_skill_and_client_guide_describe_demo_setup(self):
        skill = (ROOT / 'skills' / 'loan-origination' / 'SKILL.md').read_text()
        self.assertIn('## Demo Setup', skill)
        self.assertIn('`demoSetup`', skill)
        self.assertIn('Never offer decision cards', skill)
        guide = (ROOT / 'docs' / 'CLIENT-SETUP.md').read_text()
        self.assertIn('Demo Setup card', guide)
        self.assertIn('connectors/demo-setup-card/README.md', guide)


if __name__ == '__main__':
    unittest.main()
