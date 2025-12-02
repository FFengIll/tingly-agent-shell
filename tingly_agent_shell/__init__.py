"""
tingly_agent_shell - A shell tool for agent and target environment.

This module provides a simple interface to manage shells with proper state tracking,
command execution, and environment management.

Classes:
    AgentShell: General shell for agent use
    StateShell: Shell that tracks environment state and working directory
    SessionShell: Shell that maintains an interactive session

Public Functions:
    create_shell: Create a new AgentShell
    create_state_shell: Create a new StateShell
    create_session_shell: Create a new SessionShell
    execute_command: Execute a single command in a temporary shell
"""

from typing import Dict, List, Optional

from .hooks import (
    CommandHook,
    EchoMarkerHook,
    CommandValidator,
)
from .types import (
    ShellConfig,
    ExecuteResult,
    ShellState,
)
from .base import AgentShell
from .state_shell import StateShell
from .session_shell import SessionShell

# Alias for backward compatibility
Shell = AgentShell


# ============================================================================
# Public Utility Functions
# ============================================================================

async def create_shell(
    shell_type: str = "bash",
    environment: Optional[Dict[str, str]] = None,
    pre_scripts: Optional[List[str]] = None,
    workdir: Optional[str] = None,
) -> AgentShell:
    """
    Create a new shell with the specified configuration.

    Args:
        shell_type: Type of shell (bash, zsh, etc.)
        environment: Environment variables to set
        setup_rc: List of setup commands/scripts to run
        workdir: Working directory

    Returns:
        AgentShell instance
    """
    config = ShellConfig(
        shell_type=shell_type,
        environment=environment or {},
        pre_scripts=pre_scripts or [],
        workdir=workdir,
    )
    return AgentShell(config=config)


async def create_state_shell(
    shell_type: str = "bash",
    environment: Optional[Dict[str, str]] = None,
    pre_scripts: Optional[List[str]] = None,
    workdir: Optional[str] = None,
) -> StateShell:
    """
    Create a new state-tracking shell with the specified configuration.

    Args:
        shell_type: Type of shell (bash, zsh, etc.)
        environment: Environment variables to set
        setup_rc: List of setup commands/scripts to run
        workdir: Working directory

    Returns:
        StateShell instance
    """
    config = ShellConfig(
        shell_type=shell_type,
        environment=environment or {},
        pre_scripts=pre_scripts or [],
        workdir=workdir,
    )
    return StateShell(config=config)


async def create_session_shell(
    shell_type: str = "bash",
    environment: Optional[Dict[str, str]] = None,
    pre_scripts: Optional[List[str]] = None,
    workdir: Optional[str] = None,
) -> SessionShell:
    """
    Create a new session shell with the specified configuration.

    Args:
        shell_type: Type of shell (bash, zsh, etc.)
        environment: Environment variables to set
        setup_rc: List of setup commands/scripts to run
        workdir: Working directory

    Returns:
        SessionShell instance
    """
    config = ShellConfig(
        shell_type=shell_type,
        environment=environment or {},
        pre_scripts=pre_scripts or [],
        workdir=workdir,
    )
    return SessionShell(config=config)


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


__all__ = [
    # Classes
    'AgentShell',
    'StateShell',
    'SessionShell',
    'Shell',  # Backward compatibility alias

    # Hooks
    'CommandHook',
    'EchoMarkerHook',
    'CommandValidator',

    # Types
    'ShellConfig',
    'ShellState',
    'ExecuteResult',

    # Public functions
    'create_shell',
    'create_state_shell',
    'create_session_shell',
    'execute_command',
]
