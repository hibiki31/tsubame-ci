import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from app.services.remote_execution_service import (
    REMOTE_RUNNER_SCRIPT,
    RemoteExecutionError,
    RemoteExecutionService,
)


class FakeRemoteFile:
    def __init__(self, content: bytes):
        self.content = content

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def read(self, size=-1, offset=None):
        start = offset or 0
        if size < 0:
            return self.content[start:]
        return self.content[start : start + size]


class FakeSFTP:
    def __init__(self, content: bytes):
        self.content = content

    async def exists(self, path):
        return True

    def open(self, path, mode, encoding=None):
        return FakeRemoteFile(self.content)


class RemoteExecutionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_log_reader_preserves_utf8_boundary_between_polls(self) -> None:
        service = RemoteExecutionService()
        service.log_chunk_bytes = 1
        content = "あい".encode()
        sftp = FakeSFTP(content)

        first = await service._read_log(sftp, "stdout", 0, final=False)
        second = await service._read_log(
            sftp,
            "stdout",
            first.next_offset,
            final=False,
        )

        self.assertEqual(first.text + second.text, "あい")
        self.assertEqual(first.next_offset, 3)
        self.assertEqual(second.next_offset, len(content))
        self.assertTrue(second.eof)

    async def test_final_log_replaces_incomplete_utf8_without_stalling(self) -> None:
        service = RemoteExecutionService()
        service.log_chunk_bytes = 16
        content = b"done\n\xe3\x81"

        result = await service._read_log(
            FakeSFTP(content),
            "stdout",
            0,
            final=True,
        )

        self.assertEqual(result.text, "done\n\ufffd")
        self.assertEqual(result.next_offset, len(content))
        self.assertTrue(result.eof)

    async def test_final_multichunk_log_does_not_split_utf8(self) -> None:
        service = RemoteExecutionService()
        service.log_chunk_bytes = 1
        content = "あい".encode()
        sftp = FakeSFTP(content)

        first = await service._read_log(sftp, "stdout", 0, final=True)
        second = await service._read_log(
            sftp,
            "stdout",
            first.next_offset,
            final=True,
        )

        self.assertEqual(first.text + second.text, "あい")
        self.assertFalse(first.eof)
        self.assertTrue(second.eof)

    async def test_remote_execution_id_rejects_shell_input(self) -> None:
        with self.assertRaises(RemoteExecutionError):
            RemoteExecutionService._validate_execution_id("id; rm -rf /")


class RemoteRunnerScriptTest(unittest.TestCase):
    def test_runner_is_valid_shell_and_spools_both_streams(self) -> None:
        syntax = subprocess.run(
            ["sh", "-n"],
            input=REMOTE_RUNNER_SCRIPT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "execution"
            run_dir.mkdir()
            runner = run_dir / "runner.sh"
            script = run_dir / "script.sh"
            runner.write_text(REMOTE_RUNNER_SCRIPT)
            script.write_text(
                "printf 'standard output\\n'\n"
                "printf 'standard error\\n' >&2\n"
            )

            completed = subprocess.run(
                ["setsid", "sh", str(runner), str(run_dir)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((run_dir / "state").read_text().strip(), "finished")
            self.assertEqual((run_dir / "exit_code").read_text().strip(), "0")
            self.assertEqual(
                (run_dir / "stdout").read_text(),
                "standard output\n",
            )
            self.assertEqual(
                (run_dir / "stderr").read_text(),
                "standard error\n",
            )
            self.assertGreater(int((run_dir / "pid").read_text()), 0)

    def test_claim_directory_prevents_duplicate_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "execution"
            run_dir.mkdir()
            runner = run_dir / "runner.sh"
            script = run_dir / "script.sh"
            runner.write_text(REMOTE_RUNNER_SCRIPT)
            script.write_text("printf 'once\\n'\n")
            for _ in range(2):
                subprocess.run(
                    ["setsid", "sh", str(runner), str(run_dir)],
                    capture_output=True,
                    check=True,
                )

            self.assertEqual((run_dir / "stdout").read_text(), "once\n")

    def test_process_group_cancel_is_recorded_after_detached_start(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "execution"
            run_dir.mkdir()
            runner = run_dir / "runner.sh"
            script = run_dir / "script.sh"
            runner.write_text(REMOTE_RUNNER_SCRIPT)
            script.write_text("sleep 30\n")
            process = subprocess.Popen(
                ["setsid", "sh", str(runner), str(run_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 3
                while (
                    not (run_dir / "state").exists()
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.02)
                self.assertEqual(
                    (run_dir / "state").read_text().strip(),
                    "running",
                )

                (run_dir / "cancel_requested").touch()
                remote_pid = int((run_dir / "pid").read_text())
                os.killpg(remote_pid, signal.SIGTERM)
                process.wait(timeout=3)

                self.assertEqual(
                    (run_dir / "state").read_text().strip(),
                    "cancelled",
                )
                self.assertEqual(
                    (run_dir / "exit_code").read_text().strip(),
                    "143",
                )
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
