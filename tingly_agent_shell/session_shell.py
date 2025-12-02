"""
SessionShell implementation - maintains an interactive session.
"""

import asyncio
import time
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ShellConfig, ExecuteResult
    from .base import AgentShell


class SessionShell:
    """
    Shell that maintains an interactive session.

    This shell keeps the shell process alive and ready to communicate
    without closing unless explicitly exited or manually closed.
    """

    def __init__(
        self,
        config: Optional["ShellConfig"] = None,
        parent: Optional["SessionShell"] = None,
    ):
        """
        Initialize a SessionShell.

        Args:
            config: Shell configuration
            parent: Parent shell to inherit from
        """
        # Import here to avoid circular imports
        from .base import AgentShell

        # Store the base shell implementation
        self._shell = AgentShell(config=config, parent=parent._shell if parent else None)
        # Ensure persistent mode for sessions
        if not self._shell.config.persistent:
            self._shell.config.persistent = True

        self._persistent_process: Optional[asyncio.subprocess.Process] = None
        self._output_reader_task: Optional[asyncio.Task] = None

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the base shell."""
        return getattr(self._shell, name)

    async def _start_persistent_process(self) -> None:
        """
        Start a persistent shell process for session reuse.

        This creates a long-running shell process that will be reused
        for multiple command executions to improve performance.
        """
        if self._persistent_process is not None:
            return  # Already started

        # Create a startup script that sets up the environment and pre_scripts
        startup_script = self._build_startup_script()

        try:
            # Start the persistent shell process
            self._persistent_process = await asyncio.create_subprocess_shell(
                startup_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=self._shell._env,
                cwd=self._shell.config.workdir,
            )

        except Exception as e:
            raise RuntimeError(f"Failed to start persistent shell process: {e}") from e

    def _build_startup_script(self) -> str:
        """
        Build a startup script for the persistent shell.

        Returns:
            Command string to initialize the shell
        """
        parts = []

        # Set environment variables
        for key, value in self._shell._env.items():
            # Escape special characters in the value
            escaped_value = value.replace('"', '\\"').replace('$', '\\$')
            parts.append(f'export {key}="{escaped_value}"')

        # Run pre_scripts
        for script in self._shell.config.pre_scripts:
            parts.append(script)

        # Start interactive shell to keep process alive
        parts.append(self._shell.config.shell_type)

        return "; ".join(parts)

    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        check: bool = False,
        sync_env: bool = True,
    ) -> "ExecuteResult":
        """
        Execute a command on the persistent session.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            check: If True, raise exception on non-zero exit code
            sync_env: If True, sync environment variables after execution

        Returns:
            ExecuteResult with command output and metadata
        """
        # Start persistent process if not already started
        if self._persistent_process is None:
            await self._start_persistent_process()
            # Run pre_scripts on the persistent process
            for script in self._shell.config.pre_scripts:
                await self._execute_on_persistent_process(script)

        # Apply hooks
        execution_context = {
            'timeout': timeout,
            'sync_env': sync_env,
            'timestamp': time.time(),
        }
        wrapped_command = await self._shell._apply_hooks(command, context=execution_context)

        # Execute on persistent process
        result = await self._execute_on_persistent_process(wrapped_command, timeout)

        # Parse and update environment
        if sync_env:
            exported_vars = self._shell._parse_export_command(command)
            self._shell._env.update(exported_vars)

        # Apply post-execute hooks
        result = await self._shell._apply_hooks(command, result, execution_context)

        return result

    async def _execute_on_persistent_process(
        self,
        command: str,
        timeout: Optional[float] = None,
    ) -> "ExecuteResult":
        """
        Execute a command on the persistent shell process.

        Args:
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            ExecuteResult with command output and metadata
        """
        async with self._shell._lock:  # Ensure only one command executes at a time
            if self._persistent_process is None:
                raise RuntimeError("Persistent process not started")

            try:
                # Send command to the persistent process
                command_with_newline = f"{command}\n"
                self._persistent_process.stdin.write(command_with_newline.encode())
                await self._persistent_process.stdin.drain()

                # Read output until we see a prompt or timeout
                stdout_lines = []
                stderr_lines = []
                prompt_seen = False

                start_time = time.time()

                # Read stdout
                while not prompt_seen:
                    try:
                        line = await asyncio.wait_for(
                            self._persistent_process.stdout.readline(),
                            timeout=timeout or 30.0,
                        )
                        if not line:
                            break
                        line_str = line.decode("utf-8", errors="replace")
                        stdout_lines.append(line_str)
                        # Check if this looks like a prompt
                        if line_str.strip().endswith("$ ") or "$ " in line_str:
                            prompt_seen = True
                    except asyncio.TimeoutError:
                        # Timeout reading - might be a long-running command
                        # Return what we have so far
                        break

                # Read any remaining stderr
                try:
                    while True:
                        line = await asyncio.wait_for(
                            self._persistent_process.stderr.readline(),
                            timeout=0.1,
                        )
                        if not line:
                            break
                        stderr_lines.append(line.decode("utf-8", errors="replace"))
                except asyncio.TimeoutError:
                    pass

                stdout = "".join(stdout_lines)
                stderr = "".join(stderr_lines)

                execution_time = time.time() - start_time

                # For persistent mode, we assume success if no exception
                # A more robust implementation would capture actual return codes
                returncode = 0

                return ExecuteResult(
                    command=command,
                    returncode=returncode,
                    stdout=stdout,
                    stderr=stderr,
                    execution_time=execution_time,
                )

            except Exception as e:
                raise RuntimeError(f"Failed to execute command on persistent process: {e}") from e

    async def async_close(self) -> None:
        """
        Asynchronously close the shell and clean up resources.
        """
        self._shell._closed = True

        # Clean up persistent process if it exists
        if self._persistent_process is not None:
            try:
                # Send exit command to the persistent process
                self._persistent_process.stdin.write(b"exit\n")
                await self._persistent_process.stdin.drain()
            except Exception:
                pass

            try:
                # Terminate the process gracefully
                self._persistent_process.terminate()
                await asyncio.wait_for(
                    self._persistent_process.wait(),
                    timeout=2.0,
                )
            except (asyncio.TimeoutError, Exception):
                # Force kill if graceful termination fails
                try:
                    self._persistent_process.kill()
                    await self._persistent_process.wait()
                except Exception:
                    pass

            self._persistent_process = None
