import asyncio
import random
import string
import subprocess
from typing import AsyncIterator, Self

from absl import flags

_SSH_PATH = flags.DEFINE_string(
    name='ssh_path',
    default='/usr/bin/ssh',
    help='Path to the SSH binary.',
)
_SSH_CONFIG_PATH = flags.DEFINE_string(
    name='ssh_config_path',
    default=None,
    required=True,
    help='Path to the SSH config file.',
)
_SSH_HOST = flags.DEFINE_string(
    name='ssh_host',
    default=None,
    required=True,
    help='Name of the SSH host. The host should already be specified in SSH config file.',
)


class Router:
  CAT_SPLITTER_FILE = '/proc/cmdline'

  def __init__(self) -> None:
    subprocess.run([str(_SSH_PATH.value), '-V'], capture_output=True).check_returncode()
    self.control_path = '/tmp/ssh_' + ''.join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(16))

  async def __aenter__(self) -> Self:
    async with asyncio.timeout(5):
      self.control_master: asyncio.subprocess.Process = await asyncio.subprocess.create_subprocess_exec(
          str(_SSH_PATH.value),
          '-oBatchMode=yes',
          '-oControlMaster=yes',
          '-oControlPath=' + self.control_path,
          '-oLogLevel=DEBUG1',
          '-N',  # Do not execute a remote command.'
          '-F',  # Specifies an alternative per-user configuration file.
          str(_SSH_CONFIG_PATH.value),
          str(_SSH_HOST.value),
          stdin=asyncio.subprocess.DEVNULL,
          stdout=asyncio.subprocess.DEVNULL,
          stderr=asyncio.subprocess.PIPE,
      )
      assert self.control_master.stderr is not None

      line = ''
      while 'new mux listener' not in line and not self.control_master.stderr.at_eof():
        line = (await self.control_master.stderr.readline()).decode()

      self.cat_splitter_line = (await self.cat(self.CAT_SPLITTER_FILE))[0]
      self.cat_splitter_line += '\n'

    return self

  async def __aexit__(self, exception_type, exception_value, exception_traceback) -> None:
    self.control_master.terminate()
    async with asyncio.timeout(5):
      await self.control_master.wait()

  async def tail_follow(self, file_path: str) -> AsyncIterator[str]:
    async with asyncio.timeout(5):
      tail = await asyncio.subprocess.create_subprocess_exec(
          str(_SSH_PATH.value),
          '-oBatchMode=yes',
          '-oControlPath=' + self.control_path,
          '-F',  # Specifies an alternative per-user configuration file.
          str(_SSH_CONFIG_PATH.value),
          str(_SSH_HOST.value),
          'tail',
          '-F',
          '-n',
          '0',
          file_path,
          stdin=asyncio.subprocess.DEVNULL,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.DEVNULL,
      )

      assert tail.stdout is not None

    while not tail.stdout.at_eof():
      line = (await tail.stdout.readline()).decode().strip()
      if len(line) > 0:
        yield line

  async def cat(self, file_path: str) -> list[str]:
    async with asyncio.timeout(5):
      proc = await asyncio.subprocess.create_subprocess_exec(
          str(_SSH_PATH.value),
          '-oBatchMode=yes',
          '-oControlPath=' + self.control_path,
          '-F',  # Specifies an alternative per-user configuration file.
          str(_SSH_CONFIG_PATH.value),
          str(_SSH_HOST.value),
          'cat',
          file_path,
          stdin=asyncio.subprocess.DEVNULL,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.DEVNULL,
      )

      stdout, stderr = await proc.communicate()
      assert stderr is None

    return stdout.decode().splitlines()

  async def watch_cat(self, file_paths: set[str],
                      interval_s: float) -> AsyncIterator[dict[str, list[str]]]:
    cat_command = 'cat'
    for file_path in file_paths:
      cat_command += ' ' + file_path + ' ' + self.CAT_SPLITTER_FILE
    cat_command += '\n'

    async with asyncio.timeout(5):
      proc = await asyncio.subprocess.create_subprocess_exec(
          str(_SSH_PATH.value),
          '-oBatchMode=yes',
          '-oControlPath=' + self.control_path,
          '-F',  # Specifies an alternative per-user configuration file.
          str(_SSH_CONFIG_PATH.value),
          str(_SSH_HOST.value),
          stdin=asyncio.subprocess.PIPE,
          stdout=asyncio.subprocess.PIPE,
          stderr=asyncio.subprocess.DEVNULL,
      )

    assert proc.stdin is not None
    assert proc.stdout is not None

    while not proc.stdout.at_eof():
      proc.stdin.write(cat_command.encode())
      yield {
          file_path: (await
                      proc.stdout.readuntil(self.cat_splitter_line.encode())).decode().splitlines()
                     [:-1] for file_path in file_paths
      }
      await asyncio.sleep(interval_s)
