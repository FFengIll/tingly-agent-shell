"""
StateShell implementation - tracks environment state and working directory.
"""

import re
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ShellConfig, ExecuteResult, ShellState
    from .base import AgentShell


class StateShell:
    """
    Shell that tracks and maintains environment state and working directory.

    This shell uses command injection to keep track of current workdir and
    environment variables, ensuring state is always up-to-date.
    """

    def __init__(
        self,
        config: Optional["ShellConfig"] = None,
        parent: Optional["StateShell"] = None,
    ):
        """
        Initialize a StateShell.

        Args:
            config: Shell configuration
            parent: Parent shell to inherit from
        """
        # Import here to avoid circular imports
        from .base import AgentShell

        # Store the base shell implementation
        self._shell = AgentShell(config=config, parent=parent._shell if parent else None)
        self._last_pwd: Optional[str] = None
        self._state_sync_enabled = True

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attributes to the base shell."""
        return getattr(self._shell, name)

    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        check: bool = False,
        sync_env: bool = True,
    ) -> "ExecuteResult":
        """
        Execute a command with automatic state tracking.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            check: If True, raise exception on non-zero exit code
            sync_env: If True, sync environment variables after execution

        Returns:
            ExecuteResult with command output and metadata
        """
        # Inject state tracking commands
        command_to_execute = self._inject_state_tracking(command)

        # Execute the command
        result = await self._shell.execute(
            command_to_execute,
            timeout=timeout,
            check=check,
            sync_env=sync_env,
        )

        # Extract and update state from output
        if self._state_sync_enabled:
            self._update_state_from_output(result.stdout, result.stderr)

        return result

    def _inject_state_tracking(self, command: str) -> str:
        """
        Inject commands to track state (pwd, env) AFTER the command execution.

        Args:
            command: Original command to execute

        Returns:
            Command with state tracking injected
        """
        # State tracking commands to run AFTER the user command
        post_tracking = (
            "echo '=== STATE_PWD_START ==='; pwd; echo '=== STATE_PWD_END ==='; "
            "echo '=== STATE_ENV_START ==='; export -p; echo '=== STATE_ENV_END ==='"
        )

        # Execute the command first, then capture state afterwards
        # Run command directly (not in subshell) so cd/export take effect
        # Save exit code to preserve it after state tracking
        wrapped = f"{command}; __exit_code__=$?; {post_tracking}; exit $__exit_code__"

        return wrapped

    def _update_state_from_output(self, stdout: str, stderr: str) -> None:
        """
        Update internal state from command output.

        Args:
            stdout: Command stdout
            stderr: Command stderr
        """
        output = stdout

        # Extract PWD
        pwd_match = re.search(
            r"=== STATE_PWD_START ===\s*(.+?)\s*=== STATE_PWD_END ===",
            output,
            re.MULTILINE | re.DOTALL,
        )
        if pwd_match:
            self._last_pwd = pwd_match.group(1).strip()

        # Extract environment
        env_match = re.search(
            r"=== STATE_ENV_START ===\s*(.+?)\s*=== STATE_ENV_END ===",
            output,
            re.MULTILINE | re.DOTALL,
        )
        if env_match:
            env_output = env_match.group(1)
            self._shell._parse_and_update_env(env_output)

    def get_pwd(self) -> Optional[str]:
        """
        Get the current working directory.

        Returns:
            Current working directory or None if not tracked
        """
        return self._last_pwd

    def get_state(self) -> "ShellState":
        """
        Get current shell state.

        Returns:
            ShellState object with current pwd and env
        """
        from .types import ShellState

        return ShellState(
            pwd=self._last_pwd,
            env=self._shell.get_all_env(),
        )
