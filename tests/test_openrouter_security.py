import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
OPENROUTER = ROOT / "src" / "providers" / "openrouter.py"


class OpenRouterSecurityTest(unittest.TestCase):
    def test_openrouter_has_no_embedded_default_api_key(self):
        source = OPENROUTER.read_text(encoding="utf-8")

        self.assertNotIn("DEFAULT_API_KEY", source)
        self.assertNotRegex(source, r"sk-or-v1-[A-Za-z0-9]{40,}")
        self.assertIn("Please configure your OpenRouter API key", source)


class RepositorySecretPatternTest(unittest.TestCase):
    def test_tracked_source_files_do_not_contain_api_key_patterns(self):
        secret_pattern = re.compile(
            r"sk-or-v1-[A-Za-z0-9]{40,}|"
            r"sk-[A-Za-z0-9_-]{20,}|"
            r"sk-ant-[A-Za-z0-9_-]{20,}|"
            r"AIza[0-9A-Za-z_-]{35}|"
            r"hf_[A-Za-z0-9]{30,}|"
            r"ghp_[A-Za-z0-9]{36,}|"
            r"github_pat_[A-Za-z0-9_]{80,}|"
            r"AKIA[0-9A-Z]{16}|"
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        )
        excluded_dirs = {
            ".git",
            "build",
            "builddir",
            "dist",
            "node_modules",
            ".venv",
            "venv",
        }

        matches = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if excluded_dirs.intersection(path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            if secret_pattern.search(text):
                matches.append(str(path.relative_to(ROOT)))

        self.assertEqual([], matches)


if __name__ == "__main__":
    unittest.main()
