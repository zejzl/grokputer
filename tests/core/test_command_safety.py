"""Shared command-safety checks. These tests only call pure check functions; nothing is executed."""
import pytest

from src.core.command_safety import (
    SHELL_METACHARACTERS,
    check_command,
    find_blocked_program,
    find_shell_metacharacter,
)


class TestMetacharacters:
    @pytest.mark.parametrize("char", SHELL_METACHARACTERS)
    def test_each_listed_character_is_found(self, char):
        assert find_shell_metacharacter(f"echo a{char}b") == char

    def test_plain_command_has_none(self):
        assert find_shell_metacharacter("git status --short") is None

    def test_matches_the_list_actionexecutor_has_always_used(self):
        assert set(SHELL_METACHARACTERS) == {";", "&", "|", "<", ">", "$", "`", "\\", "\n", "\r", "%", "(", ")"}


class TestBlockedPrograms:
    @pytest.mark.parametrize(
        "command",
        [
            "format c:",
            "FORMAT.COM d:",
            "diskpart",
            "mkfs.ext4 /dev/sdb1",
            "dd if=a of=b",
            "shutdown now",
            "reboot",
            "curl http://example.test",
            "wget http://example.test",
            "nc host 80",
            "powershell -Command Get-Date",
            "cmd /c dir",
            "bash script.sh",
            "C:/Windows/System32/shutdown.exe /s",
        ],
    )
    def test_blocked(self, command):
        assert find_blocked_program(command) is not None
        assert check_command(command) is not None

    @pytest.mark.parametrize(
        "command", ["rm -rf build", "rm -fr build", "rm -r build", "rm -f a.txt", "rm --recursive build", "rm --no-preserve-root x"]
    )
    def test_unix_recursive_or_forced_delete_blocked(self, command):
        assert "delete" in find_blocked_program(command)

    @pytest.mark.parametrize("command", ["del /s /q build", "rmdir /s build", "rd /q build", "ERASE /F a.txt"])
    def test_windows_recursive_or_forced_delete_blocked(self, command):
        assert "delete" in find_blocked_program(command)

    @pytest.mark.parametrize(
        "command", ["rm a.txt", "del a.txt", "rmdir empty_dir", "ls -la", "git status", "python --version", "echo hi", "dir"]
    )
    def test_ordinary_commands_pass(self, command):
        assert check_command(command) is None

    def test_unparseable_and_empty(self):
        assert "unparseable" in find_blocked_program("echo 'unterminated")
        assert check_command("") == "empty command"
        assert check_command("   ") == "empty command"


class TestCheckCommand:
    def test_metacharacter_reported_before_program(self):
        assert "metacharacter" in check_command("echo a | cat")

    def test_block_programs_can_be_switched_off(self):
        assert check_command("format c:", block_programs=False) is None
        assert check_command("a | b", block_programs=False) is not None
