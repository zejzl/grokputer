import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # Add project root for imports

from src.executor import execute_command  # Import from src

class TestShellInjection(unittest.TestCase):
    def test_safe_command(self):
        \"\"\"Test safe command execution (e.g., ls -l).\"\"\"
        output = execute_command(\"ls -l\")
        self.assertIn(\"dir\", output.lower())  # Expect dir listing or files

    def test_injection_blocked(self):
        \"\"\"Test injection blocked (e.g., ; rm).\"\"\"
        result = execute_command(\"ls; rm -rf /\")
        self.assertIn(\"Invalid command characters\", result)

    def test_whitelist_enforced(self):
        \"\"\"Test unallowed command rejected.\"\"\"
        result = execute_command(\"rm file.txt\")
        self.assertIn(\"not allowed\", result)

    def test_malformed(self):
        \"\"\"Test malformed input.\"\"\"
        result = execute_command('ls \"unclosed')
        self.assertIn(\"Error\", result)

if __name__ == '__main__':
    unittest.main()