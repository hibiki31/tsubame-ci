"""SSH セッションから分離したリモートジョブの起動と追跡を管理する。"""

from __future__ import annotations

import asyncio
import codecs
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import posixpath
import re
import shlex
from uuid import uuid4

import asyncssh

from app.core.config import settings
from app.models.server import Server
from app.services.ssh_service import SSHConnectionError, ssh_service


REMOTE_EXECUTION_ROOT = ".local/state/tsubame-ci/executions"
REMOTE_EXECUTION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class RemoteExecutionError(Exception):
    """リモート実行プロトコルを継続できない。"""


class RemoteExecutionState(str, Enum):
    """リモート側の永続化された実行状態。"""

    MISSING = "missing"
    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RemoteLogChunk:
    """byte offset を伴うリモートログ差分。"""

    text: str
    next_offset: int
    eof: bool


@dataclass(frozen=True)
class RemoteExecutionSnapshot:
    """リモート実行の状態と、未同期ログのスナップショット。"""

    state: RemoteExecutionState
    process_id: int | None
    exit_code: int | None
    finished_at: datetime | None
    stdout: RemoteLogChunk
    stderr: RemoteLogChunk
    alive: bool

    @property
    def terminal(self) -> bool:
        return self.state in {
            RemoteExecutionState.FINISHED,
            RemoteExecutionState.CANCELLED,
        }

    @property
    def logs_complete(self) -> bool:
        return self.terminal and self.stdout.eof and self.stderr.eof


REMOTE_RUNNER_SCRIPT = r"""#!/bin/sh
set -u

run_dir=$1
umask 077

write_value() {
    destination=$1
    value=$2
    temporary="${destination}.tmp.$$"
    printf '%s\n' "$value" > "$temporary"
    mv -f "$temporary" "$destination"
}

if ! mkdir "$run_dir/claimed" 2>/dev/null; then
    exit 0
fi

: > "$run_dir/stdout"
: > "$run_dir/stderr"

if [ -f "$run_dir/cancel_requested" ]; then
    write_value "$run_dir/exit_code" 143
    write_value "$run_dir/finished_at" "$(date +%s)"
    write_value "$run_dir/state" cancelled
    exit 0
fi

write_value "$run_dir/pid" "$$"
write_value "$run_dir/pid_start_time" "$(awk '{print $22}' "/proc/$$/stat")"
write_value "$run_dir/state" running

cancelled=0
child_pid=
handle_cancel() {
    cancelled=1
    if [ -n "$child_pid" ]; then
        kill -TERM "$child_pid" 2>/dev/null || true
    fi
}
trap handle_cancel HUP INT TERM

sh "$run_dir/script.sh" > "$run_dir/stdout" 2> "$run_dir/stderr" &
child_pid=$!
wait "$child_pid"
exit_code=$?

if [ "$cancelled" -eq 1 ] || [ -f "$run_dir/cancel_requested" ]; then
    write_value "$run_dir/exit_code" 143
    write_value "$run_dir/finished_at" "$(date +%s)"
    write_value "$run_dir/state" cancelled
else
    write_value "$run_dir/exit_code" "$exit_code"
    write_value "$run_dir/finished_at" "$(date +%s)"
    write_value "$run_dir/state" finished
fi
"""


class RemoteExecutionService:
    """対象サーバ上の agentless な実行 spool を操作する。"""

    def __init__(self) -> None:
        self.log_chunk_bytes = settings.execution_log_chunk_bytes
        self.operation_timeout = (
            settings.execution_ssh_operation_timeout_seconds
        )

    async def ensure_started(
        self,
        server: Server,
        remote_execution_id: str,
        script: str,
    ) -> None:
        """実行ファイルを配置し、冪等な detached runner を起動する。"""

        self._validate_execution_id(remote_execution_id)
        conn = await ssh_service.connect(server)
        try:
            async with asyncio.timeout(self.operation_timeout):
                async with conn.start_sftp_client() as sftp:
                    run_dir = await self._resolve_run_dir(
                        sftp,
                        remote_execution_id,
                    )
                    quoted_run_dir = shlex.quote(run_dir)
                    result = await conn.run(
                        "umask 077; "
                        f"mkdir -p {shlex.quote(posixpath.dirname(run_dir))} "
                        f"{quoted_run_dir}; "
                        "command -v setsid >/dev/null 2>&1 && "
                        "command -v nohup >/dev/null 2>&1",
                        check=False,
                    )
                    if result.exit_status != 0:
                        raise RemoteExecutionError(
                            "リモート実行には mkdir、setsid、nohup が必要です"
                        )

                    suffix = uuid4().hex
                    script_temporary = f"{run_dir}/script.sh.tmp.{suffix}"
                    runner_temporary = f"{run_dir}/runner.sh.tmp.{suffix}"
                    await self._write_file(
                        sftp,
                        script_temporary,
                        script.encode(),
                    )
                    await self._write_file(
                        sftp,
                        runner_temporary,
                        REMOTE_RUNNER_SCRIPT.encode(),
                    )

                    promote_and_start = (
                        "umask 077; "
                        f"if [ ! -e {shlex.quote(run_dir + '/script.sh')} ]; then "
                        f"mv {shlex.quote(script_temporary)} "
                        f"{shlex.quote(run_dir + '/script.sh')}; "
                        f"else rm -f {shlex.quote(script_temporary)}; fi; "
                        f"if [ ! -e {shlex.quote(run_dir + '/runner.sh')} ]; then "
                        f"mv {shlex.quote(runner_temporary)} "
                        f"{shlex.quote(run_dir + '/runner.sh')}; "
                        f"else rm -f {shlex.quote(runner_temporary)}; fi; "
                        f"chmod 600 {shlex.quote(run_dir + '/script.sh')} "
                        f"{shlex.quote(run_dir + '/runner.sh')}; "
                        f"nohup setsid sh {shlex.quote(run_dir + '/runner.sh')} "
                        f"{quoted_run_dir} >/dev/null 2>&1 </dev/null &"
                    )
                    result = await conn.run(promote_and_start, check=False)
                    if result.exit_status != 0:
                        raise RemoteExecutionError(
                            "リモート実行ファイルの配置または起動に失敗しました"
                        )
        except RemoteExecutionError:
            raise
        except (asyncio.TimeoutError, OSError, asyncssh.Error) as error:
            raise SSHConnectionError(f"SSH通信エラー: {error}") from error
        finally:
            conn.close()
            await conn.wait_closed()

    async def snapshot(
        self,
        server: Server,
        remote_execution_id: str,
        stdout_offset: int,
        stderr_offset: int,
    ) -> RemoteExecutionSnapshot:
        """永続化された状態と指定 offset 以降のログを取得する。"""

        self._validate_execution_id(remote_execution_id)
        conn = await ssh_service.connect(server)
        try:
            async with asyncio.timeout(self.operation_timeout):
                async with conn.start_sftp_client() as sftp:
                    run_dir = await self._resolve_run_dir(
                        sftp,
                        remote_execution_id,
                    )
                    if not await sftp.exists(run_dir):
                        empty_stdout = RemoteLogChunk("", stdout_offset, False)
                        empty_stderr = RemoteLogChunk("", stderr_offset, False)
                        return RemoteExecutionSnapshot(
                            state=RemoteExecutionState.MISSING,
                            process_id=None,
                            exit_code=None,
                            finished_at=None,
                            stdout=empty_stdout,
                            stderr=empty_stderr,
                            alive=False,
                        )

                    state_value = await self._read_text(sftp, f"{run_dir}/state")
                    state = self._parse_state(state_value)
                    process_id = self._parse_integer(
                        await self._read_text(sftp, f"{run_dir}/pid")
                    )
                    exit_code = self._parse_integer(
                        await self._read_text(sftp, f"{run_dir}/exit_code")
                    )
                    finished_epoch = self._parse_integer(
                        await self._read_text(sftp, f"{run_dir}/finished_at")
                    )
                    finished_at = (
                        datetime.fromtimestamp(finished_epoch, tz=timezone.utc)
                        if finished_epoch is not None
                        else None
                    )

                    stdout = await self._read_log(
                        sftp,
                        f"{run_dir}/stdout",
                        stdout_offset,
                        final=state in {
                            RemoteExecutionState.FINISHED,
                            RemoteExecutionState.CANCELLED,
                        },
                    )
                    stderr = await self._read_log(
                        sftp,
                        f"{run_dir}/stderr",
                        stderr_offset,
                        final=state in {
                            RemoteExecutionState.FINISHED,
                            RemoteExecutionState.CANCELLED,
                        },
                    )
                    alive = await self._is_alive(
                        conn,
                        sftp,
                        run_dir,
                        process_id,
                    )
                    return RemoteExecutionSnapshot(
                        state=state,
                        process_id=process_id,
                        exit_code=exit_code,
                        finished_at=finished_at,
                        stdout=stdout,
                        stderr=stderr,
                        alive=alive,
                    )
        except (ValueError, UnicodeError) as error:
            raise RemoteExecutionError(
                f"リモート実行状態を解釈できません: {error}"
            ) from error
        except (asyncio.TimeoutError, OSError, asyncssh.Error) as error:
            raise SSHConnectionError(f"SSH通信エラー: {error}") from error
        finally:
            conn.close()
            await conn.wait_closed()

    async def request_cancel(
        self,
        server: Server,
        remote_execution_id: str,
    ) -> None:
        """キャンセル印を永続化し、同一 process group へ TERM を送る。"""

        self._validate_execution_id(remote_execution_id)
        conn = await ssh_service.connect(server)
        try:
            async with asyncio.timeout(self.operation_timeout):
                async with conn.start_sftp_client() as sftp:
                    run_dir = await self._resolve_run_dir(
                        sftp,
                        remote_execution_id,
                    )
                    quoted_run_dir = shlex.quote(run_dir)
                    command = (
                        f"if [ ! -d {quoted_run_dir} ]; then exit 0; fi; "
                        f": > {shlex.quote(run_dir + '/cancel_requested')}; "
                        f"state=$(cat {shlex.quote(run_dir + '/state')} "
                        "2>/dev/null || true); "
                        'if [ "$state" = finished ] || [ "$state" = cancelled ]; '
                        "then exit 0; fi; "
                        f"pid=$(cat {shlex.quote(run_dir + '/pid')} "
                        "2>/dev/null || true); "
                        f"expected=$(cat {shlex.quote(run_dir + '/pid_start_time')} "
                        "2>/dev/null || true); "
                        'case "$pid" in ""|*[!0-9]*) exit 0;; esac; '
                        'actual=$(awk \'{print $22}\' "/proc/$pid/stat" '
                        "2>/dev/null || true); "
                        'if [ -n "$expected" ] && [ "$actual" = "$expected" ]; then '
                        'kill -TERM -- "-$pid" 2>/dev/null || true; '
                        "fi"
                    )
                    result = await conn.run(command, check=False)
                    if result.exit_status != 0:
                        raise RemoteExecutionError(
                            "リモート実行へキャンセルを要求できませんでした"
                        )
        except RemoteExecutionError:
            raise
        except (asyncio.TimeoutError, OSError, asyncssh.Error) as error:
            raise SSHConnectionError(f"SSH通信エラー: {error}") from error
        finally:
            conn.close()
            await conn.wait_closed()

    @staticmethod
    async def _resolve_run_dir(sftp, remote_execution_id: str) -> str:
        home = str(await sftp.realpath("."))
        return posixpath.join(home, REMOTE_EXECUTION_ROOT, remote_execution_id)

    @staticmethod
    async def _write_file(sftp, path: str, content: bytes) -> None:
        async with sftp.open(path, "w", encoding=None) as remote_file:
            await remote_file.write(content)

    @staticmethod
    async def _read_text(sftp, path: str) -> str | None:
        if not await sftp.exists(path):
            return None
        async with sftp.open(path, "r", encoding=None) as remote_file:
            content = await remote_file.read()
        return content.decode("utf-8", errors="strict").strip()

    async def _read_log(
        self,
        sftp,
        path: str,
        offset: int,
        *,
        final: bool,
    ) -> RemoteLogChunk:
        if not await sftp.exists(path):
            return RemoteLogChunk("", offset, False)

        read_size = self.log_chunk_bytes + 4
        async with sftp.open(path, "r", encoding=None) as remote_file:
            content = await remote_file.read(read_size, offset=offset)

        at_eof = len(content) < read_size
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        text = decoder.decode(content, final=final and at_eof)
        pending, _ = decoder.getstate()
        consumed = len(content) - len(pending)
        return RemoteLogChunk(
            text=text,
            next_offset=offset + consumed,
            eof=at_eof and not pending,
        )

    async def _is_alive(
        self,
        conn,
        sftp,
        run_dir: str,
        process_id: int | None,
    ) -> bool:
        if process_id is None:
            return False
        expected = await self._read_text(sftp, f"{run_dir}/pid_start_time")
        if not expected:
            return False
        result = await conn.run(
            f"actual=$(awk '{{print $22}}' /proc/{process_id}/stat "
            "2>/dev/null || true); "
            f"[ \"$actual\" = {shlex.quote(expected)} ]",
            check=False,
        )
        return result.exit_status == 0

    @staticmethod
    def _parse_state(value: str | None) -> RemoteExecutionState:
        if value is None:
            return RemoteExecutionState.STARTING
        try:
            return RemoteExecutionState(value)
        except ValueError as error:
            raise ValueError(f"未知の状態です: {value}") from error

    @staticmethod
    def _parse_integer(value: str | None) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    @staticmethod
    def _validate_execution_id(remote_execution_id: str) -> None:
        if not REMOTE_EXECUTION_ID_PATTERN.fullmatch(remote_execution_id):
            raise RemoteExecutionError("不正なリモート実行IDです")


remote_execution_service = RemoteExecutionService()
