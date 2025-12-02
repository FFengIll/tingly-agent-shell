"""
Data types and configuration classes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tingly_agent_shell.hooks import CommandHook


@dataclass
class ShellConfig:
    """Configuration for shell initialization."""

    shell_type: str = "bash"
    environment: Dict[str, str] = field(default_factory=dict)
    pre_scripts: List[str] = field(default_factory=list)
    workdir: Optional[str] = None
    persistent: bool = True  # Enable persistent shell session by default
    # Command hooks to process commands before/after execution
    hooks: List["CommandHook"] = field(default_factory=list)


@dataclass
class ShellState:
    """Represents the current shell state including working directory and environment."""

    pwd: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecuteResult:
    """Result of a command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    execution_time: float
