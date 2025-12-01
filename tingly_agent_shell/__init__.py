"""
tingly_agent_shell - A shell tool for agent and target environment.

This module provides a simple interface to manage shells with proper state tracking,
command execution, and environment management.
"""

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class ShellConfig:
    """Configuration for shell initialization."""
    shell_type: str = "bash"
    environment: Dict[str, str] = field(default_factory=dict)
    setup_rc: List[str] = field(default_factory=list)
    workdir: Optional[str] = None


@dataclass
class ExecuteResult:
    """Result of a command execution."""
    command: str
    returncode: int
    stdout: str
    stderr: str
    execution_time: float


class Shell:
    """
    A shell manager that provides async command execution and state management.

    Features:
    - Initialize shell with custom environment and setup
    - Fork new shells inheriting parent state
    - Execute commands with timeout control
    - Track shell environment and execution state
    """

    def __init__(
        self,
        config: Optional[ShellConfig] = None,
        parent: Optional["Shell"] = None,
    ):
        """
        Initialize a shell.

        Args:
            config: Shell configuration with type, environment, and setup
            parent: Parent shell to inherit from (for forking)
        """
        self.config = config or ShellConfig()
        self.parent = parent
        self._process: Optional[subprocess.Popen] = None
        self._closed = False

        # Initialize environment by inheriting from parent or config
        self._env = os.environ.copy()
        if parent:
            self._env.update(parent._env)
        else:
            self._env.update(self.config.environment)

        # Run setup RC scripts
        self._run_setup_rc()

    def _run_setup_rc(self) -> None:
        """
        Run setup RC scripts/commands to initialize the shell.
        This runs synchronously during shell initialization.
        We parse commands to extract environment changes rather than executing them,
        because subprocesses are isolated and won't persist environment changes.
        """
        # Parse setup commands to extract environment variables
        for cmd in self.config.setup_rc:
            try:
                # Parse export commands from setup
                exported_vars = self._parse_export_command(cmd)
                self._env.update(exported_vars)
            except Exception:
                # If setup fails, silently continue
                pass

    def _parse_export_command(self, command: str) -> Dict[str, str]:
        """
        Parse export commands to extract environment variable changes.

        Args:
            command: Command string that may contain export statements

        Returns:
            Dictionary of environment variables extracted from the command
        """
        import re

        env_vars = {}

        # Pattern to match: export VAR="value" or export VAR=value
        # Also handles: export VAR="value" PATH="new:$PATH"
        patterns = [
            r'export\s+(\w+)="([^"]*)"',  # export VAR="value"
            r"export\s+(\w+)='([^']*)'",  # export VAR='value'
            r'export\s+(\w+)=([^\s]+?)(?:\s+|$)',   # export VAR=value (no spaces) - non-greedy
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, command)
            for match in matches:
                key = match.group(1)
                value = match.group(2)
                # Strip quotes if present
                value = value.strip('"').strip("'")
                # Expand variables like $PATH
                value = self._expand_env_vars(value)
                env_vars[key] = value

        return env_vars

    def _expand_env_vars(self, value: str) -> str:
        """
        Expand environment variables in a value string.

        Args:
            value: String that may contain $VAR or ${VAR}

        Returns:
            String with environment variables expanded
        """
        import re

        # Replace ${VAR} and $VAR patterns
        def replace_var(match):
            var_name = match.group(1)
            return self._env.get(var_name, match.group(0))

        # Match both ${VAR} and $VAR
        pattern = r'\$\{?(\w+)\}?'
        expanded = re.sub(pattern, replace_var, value)

        return expanded

    async def _sync_env_from_shell(self) -> None:
        """
        Sync environment variables from the shell.
        This captures exported environment variables.

        Tries multiple methods in order for maximum portability:
        1. 'env' command (available on most Unix-like systems)
        2. 'printenv' command (Unix systems, not on Windows)
        3. Falls back to no sync if neither is available
        """
        # Try 'env' first (more portable than printenv)
        if await self._try_sync_with_command("env"):
            return

        # Fall back to 'printenv' if 'env' is not available
        if await self._try_sync_with_command("printenv"):
            return

        # If neither command is available, silently skip sync
        # The shell will continue to use its internal _env tracking
        pass

    async def _try_sync_with_command(self, command: str) -> bool:
        """
        Attempt to sync environment using a specific command.

        Args:
            command: The command to use for syncing ('env', 'printenv', etc.)

        Returns:
            True if sync succeeded, False if command not available or failed
        """
        try:
            # Run the command to get all environment variables
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
                cwd=self.config.workdir,
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode("utf-8")
                # Parse command output (KEY=VALUE per line)
                for line in output.splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Only update if the value is different
                        if self._env.get(key) != value:
                            self._env[key] = value
                return True
            return False
        except Exception:
            # If command fails (e.g., not available on this platform), silently continue
            return False

    def _parse_and_update_env(self, export_output: str) -> None:
        """
        Parse 'export -p' output and update environment variables.

        Args:
            export_output: Output from 'export -p' command
        """
        import re

        # Parse lines like: declare -x VAR="value"
        # or: export VAR="value"
        pattern = r'declare\s+-x\s+(\w+)="([^"]*)"|export\s+(\w+)="([^"]*)"'

        for line in export_output.splitlines():
            match = re.search(pattern, line)
            if match:
                # Handle both patterns
                key = match.group(1) if match.group(1) else match.group(3)
                value = match.group(2) if match.group(2) else match.group(4)

                # Update environment
                self._env[key] = value

    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        check: bool = False,
        sync_env: bool = True,
    ) -> ExecuteResult:
        """
        Execute a command in the shell.

        Args:
            command: Command to execute
            timeout: Timeout in seconds (None for no timeout)
            check: If True, raise exception on non-zero exit code

        Returns:
            ExecuteResult with command output and metadata

        Raises:
            asyncio.TimeoutError: If command times out
            subprocess.CalledProcessError: If check=True and command fails
        """
        if self._closed:
            raise RuntimeError("Shell is closed")

        # Record start time
        import time
        start_time = time.time()

        try:
            # Execute command using subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
                cwd=self.config.workdir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                try:
                    await process.wait()
                except Exception:
                    pass
                # Re-raise TimeoutError without wrapping it
                raise

            execution_time = time.time() - start_time

            result = ExecuteResult(
                command=command,
                returncode=process.returncode,
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
                execution_time=execution_time,
            )

            # Parse and update environment BEFORE execution (predictive approach)
            # This updates _env based on commands that will affect environment
            if sync_env:
                exported_vars = self._parse_export_command(command)
                self._env.update(exported_vars)

            # Sync environment variables from the shell AFTER execution
            # This gets the actual state from the subprocess
            if sync_env and process.returncode == 0:
                await self._sync_env_from_shell()

            if check and process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    command,
                    output=stdout,
                    stderr=stderr,
                )

            return result

        except asyncio.TimeoutError:
            # Don't wrap TimeoutError
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            raise RuntimeError(
                f"Failed to execute command '{command}': {e}"
            ) from e

    def fork(self, config: Optional[ShellConfig] = None) -> "Shell":
        """
        Fork a new shell inheriting this shell's environment.

        Args:
            config: Optional configuration for the forked shell

        Returns:
            New Shell instance with inherited environment and state
        """
        if self._closed:
            raise RuntimeError("Cannot fork from closed shell")

        if config:
            # Merge inherited env with new config env
            merged_env = self._env.copy()
            merged_env.update(config.environment)
            config.environment = merged_env
            # Inherit shell type and other settings
            if not config.shell_type:
                config.shell_type = self.config.shell_type
            if not config.workdir:
                config.workdir = self.config.workdir
        else:
            # Create config inheriting all from parent
            config = ShellConfig(
                shell_type=self.config.shell_type,
                environment=self._env.copy(),
                setup_rc=self.config.setup_rc.copy(),
                workdir=self.config.workdir,
            )

        return Shell(config=config, parent=self)

    def setenv(self, key: str, value: str) -> None:
        """
        Set an environment variable in this shell.

        Args:
            key: Environment variable name
            value: Environment variable value
        """
        if self._closed:
            raise RuntimeError("Shell is closed")
        self._env[key] = value

    def getenv(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable from this shell.

        Args:
            key: Environment variable name
            default: Default value if key not found

        Returns:
            Environment variable value or default
        """
        return self._env.get(key, default)

    def get_all_env(self) -> Dict[str, str]:
        """
        Get all environment variables for this shell.

        Returns:
            Dictionary of all environment variables
        """
        return self._env.copy()

    def get_config(self) -> ShellConfig:
        """
        Get the current shell configuration.

        Returns:
            ShellConfig object
        """
        return self.config

    async def execute_script(
        self,
        script_path: str,
        timeout: Optional[float] = None,
    ) -> ExecuteResult:
        """
        Execute a shell script file.

        Args:
            script_path: Path to the script file
            timeout: Timeout in seconds (None for no timeout)

        Returns:
            ExecuteResult with command output and metadata
        """
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")

        if not os.access(script_path, os.R_OK):
            raise PermissionError(f"Cannot read script: {script_path}")

        # Make script executable
        os.chmod(script_path, 0o755)

        # Execute the script
        return await self.execute(f"'{script_path}'", timeout=timeout)

    async def test_command(self, command: str) -> bool:
        """
        Test if a command is available in this shell.

        Args:
            command: Command to test

        Returns:
            True if command is available, False otherwise
        """
        try:
            result = await self.execute(f"command -v {command}", timeout=5.0)
            return result.returncode == 0
        except Exception:
            return False

    def is_alive(self) -> bool:
        """
        Check if the shell is alive (not closed).

        Returns:
            True if shell is not closed
        """
        return not self._closed

    def close(self) -> None:
        """
        Close the shell and clean up resources.
        """
        self._closed = True
        # Note: subprocess.Popen instances are created per-execute,
        # so we don't need to track or kill them explicitly

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


# Convenience functions for quick usage

async def create_shell(
    shell_type: str = "bash",
    environment: Optional[Dict[str, str]] = None,
    setup_rc: Optional[List[str]] = None,
    workdir: Optional[str] = None,
) -> Shell:
    """
    Create a new shell with the specified configuration.

    Args:
        shell_type: Type of shell (bash, zsh, etc.)
        environment: Environment variables to set
        setup_rc: List of setup commands/scripts to run
        workdir: Working directory

    Returns:
        Shell instance
    """
    config = ShellConfig(
        shell_type=shell_type,
        environment=environment or {},
        setup_rc=setup_rc or [],
        workdir=workdir,
    )
    return Shell(config=config)


async def execute_command(
    command: str,
    timeout: Optional[float] = None,
    environment: Optional[Dict[str, str]] = None,
    check: bool = False,
) -> ExecuteResult:
    """
    Execute a single command in a temporary shell.

    Args:
        command: Command to execute
        timeout: Timeout in seconds
        environment: Environment variables
        check: If True, raise exception on non-zero exit code

    Returns:
        ExecuteResult with command output and metadata
    """
    async with await create_shell(environment=environment) as shell:
        return await shell.execute(command, timeout=timeout, check=check)
