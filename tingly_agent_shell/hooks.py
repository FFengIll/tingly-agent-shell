"""
Command Hook System - Extensible framework for command pre/post processing.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable


class CommandHook(ABC):
    """
    Abstract base class for command hooks.

    Hooks allow modifying commands before/after execution without coupling
    to the core Shell implementation. This provides a clean separation of concerns.
    """

    @abstractmethod
    async def pre_execute(self, command: str, context: Dict[str, Any]) -> str:
        """
        Process command before execution.

        Args:
            command: Original command
            context: Execution context (timeout, env, etc.)

        Returns:
            Modified command to execute
        """
        pass

    @abstractmethod
    async def post_execute(
        self,
        command: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Process result after execution.

        Args:
            command: Executed command
            result: Execution result
            context: Execution context

        Returns:
            Modified result (can be the same or wrapped)
        """
        pass


class EchoMarkerHook(CommandHook):
    """
    Command hook that adds echo markers before and after command execution.

    This hook wraps commands with echo statements to mark the start and end
    of command execution, useful for debugging and tracking in persistent sessions.

    Features:
    - Unique markers per execution to avoid conflicts
    - Configurable marker format
    - Automatic cleanup of marker output from results
    - Independent of Shell class - pure hook pattern
    """

    def __init__(
        self,
        enabled: bool = True,
        marker_format: Optional[Callable[[str], str]] = None,
        include_timestamp: bool = True,
        include_command_hash: bool = True,
    ):
        """
        Initialize EchoMarkerHook.

        Args:
            enabled: Whether the hook is active
            marker_format: Custom function to generate marker text
            include_timestamp: Add timestamp to markers
            include_command_hash: Add hash of command to markers
        """
        self.enabled = enabled
        self.marker_format = marker_format or self._default_marker_format
        self.include_timestamp = include_timestamp
        self.include_command_hash = include_command_hash
        self._execution_counter = 0

    def _default_marker_format(self, execution_id: str, event: str) -> str:
        """
        Default marker format generator.

        Args:
            execution_id: Unique identifier for this execution
            event: Either 'start' or 'end'

        Returns:
            Formatted marker string
        """
        parts = [f"CMD_MARKER_{event.upper()}"]
        parts.append(execution_id)

        if self.include_timestamp:
            import time
            parts.append(f"TS_{int(time.time())}")

        if self.include_command_hash:
            import hashlib
            # Short hash will be added later

        return "_".join(parts)

    def _generate_execution_id(self) -> str:
        """Generate unique execution ID."""
        self._execution_counter += 1
        # Combine counter with UUID for uniqueness
        return f"{self._execution_counter}_{uuid.uuid4().hex[:8]}"

    def _hash_command(self, command: str) -> str:
        """Generate short hash of command."""
        import hashlib
        return hashlib.md5(command.encode()).hexdigest()[:8]

    async def pre_execute(self, command: str, context: Dict[str, Any]) -> str:
        """
        Wrap command with start and end markers.

        Args:
            command: Original command
            context: Execution context

        Returns:
            Command wrapped with start and end echo markers
        """
        if not self.enabled:
            return command

        execution_id = self._generate_execution_id()
        command_hash = self._hash_command(command) if self.include_command_hash else None

        # Store context for post_execute
        context['_echo_marker_id'] = execution_id
        context['_echo_marker_hash'] = command_hash
        context['_command_hash'] = command_hash

        # Generate marker text
        start_marker = self.marker_format(execution_id, 'start')
        end_marker = self.marker_format(execution_id, 'end')

        # Wrap command with both start and end markers
        # Format: echo "=== START ===" && command && echo "=== END ==="
        wrapped = f'echo "=== CMD_MARKER_START_{execution_id} ===" && {command} && echo "=== CMD_MARKER_END_{execution_id} ==="'

        return wrapped

    async def post_execute(
        self,
        command: str,
        result: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Process result and clean up markers.

        Args:
            command: Original command (before wrapping)
            result: Execution result
            context: Execution context

        Returns:
            Result with marker output cleaned
        """
        if not self.enabled:
            return result

        # The command passed here should be the original unwrapped command
        # that was passed to pre_execute
        original = command

        # Get stored context
        execution_id = context.get('_echo_marker_id')
        command_hash = context.get('_echo_marker_hash')

        if execution_id:
            # Clean marker output from stdout
            cleaned_stdout = self._clean_markers(result.stdout, execution_id, command_hash)

            # Create new result with cleaned output
            # Note: We need to handle this dynamically since ExecuteResult is in types module
            result_dict = {
                'command': original,
                'returncode': result.returncode,
                'stdout': cleaned_stdout,
                'stderr': result.stderr,
                'execution_time': result.execution_time,
            }

            # Import ExecuteResult dynamically to avoid circular imports
            from tingly_agent_shell.types import ExecuteResult
            cleaned_result = ExecuteResult(**result_dict)

            return cleaned_result

        return result

    def _clean_markers(
        self,
        output: str,
        execution_id: str,
        command_hash: Optional[str]
    ) -> str:
        """
        Remove marker lines from output.

        Args:
            output: Raw command output
            execution_id: Execution identifier
            command_hash: Hash of original command (unused but kept for compatibility)

        Returns:
            Output with markers removed
        """
        lines = output.splitlines()
        cleaned_lines = []

        for line in lines:
            # Skip lines that contain our markers
            # Match both "CMD_MARKER_START_id" and "CMD_MARKER_END_id"
            if f"CMD_MARKER_START_{execution_id}" in line:
                continue
            if f"CMD_MARKER_END_{execution_id}" in line:
                continue
            # Also skip the formatted echo lines
            if f"=== CMD_MARKER_START_{execution_id} ===" in line:
                continue
            if f"=== CMD_MARKER_END_{execution_id} ===" in line:
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)


class CommandValidator:
    """
    Validator to check command execution boundaries using markers.

    This validator can verify that:
    1. Commands have proper start/end markers
    2. Output is complete (no truncation)
    3. No interleaving between commands in persistent sessions
    """

    def __init__(self, hook: Optional[EchoMarkerHook] = None):
        """
        Initialize validator.

        Args:
            hook: The EchoMarkerHook instance to validate against
        """
        self.hook = hook
        self._execution_log: List[Dict[str, Any]] = []

    def validate_execution(
        self,
        command: str,
        result: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate command execution.

        Args:
            command: Executed command
            result: Execution result
            context: Optional execution context

        Returns:
            Validation report with status and details
        """
        context = context or {}

        report = {
            'valid': True,
            'issues': [],
            'command': command,
            'returncode': result.returncode,
        }

        # Check if hook was used
        if self.hook and self.hook.enabled:
            execution_id = context.get('_echo_marker_id')
            command_hash = context.get('_echo_marker_hash')

            if execution_id:
                # Verify markers are present
                has_start = f"CMD_MARKER_START_{execution_id}" in result.stdout
                has_end = f"CMD_MARKER_END_{execution_id}" in result.stdout

                # Log execution
                self._execution_log.append({
                    'execution_id': execution_id,
                    'command': command,
                    'has_start_marker': has_start,
                    'has_end_marker': has_end,
                    'timestamp': context.get('timestamp'),
                })

                if not has_start:
                    report['valid'] = False
                    report['issues'].append('Missing start marker')

                if not has_end:
                    report['valid'] = False
                    report['issues'].append('Missing end marker')

                # Check for interleaving
                interleaving = self._check_interleaving(execution_id)
                if interleaving:
                    report['valid'] = False
                    report['issues'].append(f'Output interleaving detected: {interleaving}')

        return report

    def _check_interleaving(self, current_execution_id: str) -> Optional[str]:
        """
        Check if output from other commands interleaved with current execution.

        Args:
            current_execution_id: ID of current execution

        Returns:
            Description of interleaving issue if found
        """
        # This is a simplified check - in a real implementation,
        # you would track the order of marker appearances
        current_idx = None
        for i, entry in enumerate(self._execution_log):
            if entry['execution_id'] == current_execution_id:
                current_idx = i
                break

        if current_idx is not None and current_idx < len(self._execution_log) - 1:
            next_entry = self._execution_log[current_idx + 1]
            if not next_entry['has_start_marker']:
                return "Next command started before current finished"

        return None

    def get_execution_log(self) -> List[Dict[str, Any]]:
        """
        Get log of all executions.

        Returns:
            List of execution records
        """
        return self._execution_log.copy()
