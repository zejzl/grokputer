import unittest
import sys
import os
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # Add project root for imports

from src.executor import execute_command  # Import from src


class TestShellInjection(unittest.TestCase):
    def test_safe_command(self):
        """Allowed command runs and returns its output (echo works on Windows and POSIX)."""
        output = execute_command("echo hello")
        self.assertIn("hello", output)

    def test_injection_blocked(self):
        """Shell metacharacters are rejected before anything runs."""
        for command in ("ls; rm -rf /", "echo a && echo b", "echo a | cat", "echo $(whoami)", "echo a > out.txt"):
            with self.subTest(command=command):
                self.assertIn("Invalid command characters", execute_command(command))

    def test_whitelist_enforced(self):
        """Unallowed command rejected."""
        result = execute_command("rm file.txt")
        self.assertIn("not allowed", result)

    def test_malformed(self):
        """Unbalanced quotes are reported instead of being passed to a shell."""
        result = execute_command('echo "unclosed')
        self.assertIn("Malformed command", result)

    def test_never_uses_shell(self):
        """subprocess is called with an argument list and shell=False."""
        with mock.patch("src.executor.subprocess.run") as run:
            run.return_value = mock.Mock(stdout="ok", stderr="")
            execute_command("echo hi there")
        args, kwargs = run.call_args
        self.assertIsInstance(args[0], list)
        self.assertIs(kwargs.get("shell"), False)

    def test_missing_binary_reported(self):
        """A whitelisted command that is not installed gives a clear message."""
        with mock.patch("src.executor.subprocess.run", side_effect=FileNotFoundError):
            self.assertIn("not found", execute_command("tail -n 1 x.txt"))


if __name__ == "__main__":
    unittest.main()
