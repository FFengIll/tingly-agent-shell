# Tingly Agent Shell

A Python module for managing shells with proper state tracking, command execution, and environment management. Built specifically for AI agents working with various target environments.

## Features

- **Shell Initialization**: Create shells with custom environment variables, setup scripts, and shell types
- **Shell Forking**: Fork new shells that inherit all environment state from parent shells
- **Async Command Execution**: Execute commands asynchronously with timeout control
- **Environment Variable Tracking**: Automatically tracks environment variable changes from `export` commands
- **Multiple Setup Scripts**: Support for multiple initialization commands (not just one)
- **State Management**: Track and manage shell environment and execution state
- **Cross-Platform**: Uses Python's built-in `subprocess` module for compatibility
- **No External Dependencies**: Pure Python implementation with no external dependencies

## Installation

```bash
pip install tingly-agent-shell
```

## Quick Start

### Basic Usage

```python
import asyncio
from tingly_agent_shell import create_shell, execute_command

# Execute a single command
async def simple_example():
    result = await execute_command("echo 'Hello, World!'")
    print(f"Output: {result.stdout}")
    print(f"Exit code: {result.returncode}")

# Run with async/await
asyncio.run(simple_example())
```

### Working with Shell Instances

```python
import asyncio
from tingly_agent_shell import create_shell

async def shell_example():
    # Create a shell with custom environment
    shell = await create_shell(
        shell_type="bash",
        environment={
            "MY_VAR": "my_value",
            "PATH": "/custom/path"
        }
    )

    # Execute commands
    result = await shell.execute("echo $MY_VAR")
    print(result.stdout)  # Output: my_value

    # Set new environment variable via export
    await shell.execute("export NEW_VAR='new_value'")
    # The variable is now tracked automatically!
    value = shell.getenv("NEW_VAR")
    print(value)  # Output: new_value

    # Fork a new shell inheriting all state
    child_shell = shell.fork()
    print(child_shell.getenv("NEW_VAR"))  # Output: new_value
    print(child_shell.getenv("MY_VAR"))   # Output: my_value

    # Close when done
    shell.close()

asyncio.run(shell_example())
```

### Multiple Setup Scripts

```python
import asyncio
from tingly_agent_shell import create_shell

async def setup_example():
    # Create shell with multiple setup commands
    shell = await create_shell(
        setup_rc=[
            "export DATABASE_URL='postgresql://localhost/mydb'",
            "export API_KEY='secret123'",
            "export FEATURE_FLAG='enabled'"
        ]
    )

    # All setup variables are available immediately
    print(shell.getenv("DATABASE_URL"))  # Output: postgresql://localhost/mydb
    print(shell.getenv("API_KEY"))       # Output: secret123
    print(shell.getenv("FEATURE_FLAG"))  # Output: enabled

asyncio.run(setup_example())
```

### Using Context Manager

```python
import asyncio
from tingly_agent_shell import create_shell

async def context_manager_example():
    async with await create_shell() as shell:
        result = await shell.execute("pwd")
        print(f"Current directory: {result.stdout}")

        # Commands execute in the shell context
        result = await shell.execute("ls -la")
        print(f"Directory listing:\n{result.stdout}")

asyncio.run(context_manager_example())
```

### Executing Scripts

```python
import asyncio
import tempfile
import os
from tingly_agent_shell import create_shell

async def script_example():
    # Create a temporary script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write('#!/bin/bash\necho "Hello from script!"\n')
        script_path = f.name

    try:
        async with await create_shell() as shell:
            result = await shell.execute_script(script_path)
            print(result.stdout)  # Output: Hello from script!
    finally:
        os.unlink(script_path)

asyncio.run(script_example())
```

### Working with Different Shell Types

```python
import asyncio
from tingly_agent_shell import create_shell

async def shell_types_example():
    # Create a zsh shell
    zsh_shell = await create_shell(shell_type="zsh")
    result = await zsh_shell.execute("echo $SHELL")
    print(result.stdout)

    # Create a bash shell
    bash_shell = await create_shell(shell_type="bash")
    result = await bash_shell.execute("echo $SHELL")
    print(result.stdout)

asyncio.run(shell_types_example())
```

### Timeout Control

```python
import asyncio
from tingly_agent_shell import create_shell

async def timeout_example():
    shell = await create_shell()

    try:
        # This will timeout after 2 seconds
        result = await shell.execute("sleep 5", timeout=2.0)
    except asyncio.TimeoutError:
        print("Command timed out!")

asyncio.run(timeout_example())
```

### Error Handling

```python
import asyncio
from tingly_agent_shell import create_shell

async def error_example():
    shell = await create_shell()

    # Execute a command that will fail
    result = await shell.execute("false", check=False)
    print(f"Exit code: {result.returncode}")  # Output: 1

    # Execute with check=True to raise exception
    try:
        result = await shell.execute("false", check=True)
    except Exception as e:
        print(f"Command failed: {e}")

asyncio.run(error_example())
```

## API Reference

### Classes

#### `Shell`
The main shell management class.

**Methods:**
- `__init__(config, parent)`: Initialize a shell
- `execute(command, timeout, check)`: Execute a command
- `fork(config)`: Fork a new shell inheriting parent state
- `setenv(key, value)`: Set environment variable
- `getenv(key, default)`: Get environment variable
- `get_all_env()`: Get all environment variables
- `get_config()`: Get shell configuration
- `execute_script(script_path, timeout)`: Execute a script file
- `test_command(command)`: Test if command is available
- `is_alive()`: Check if shell is alive
- `close()`: Close the shell

#### `ShellConfig`
Configuration for shell initialization.

**Fields:**
- `shell_type`: Shell type (default: "bash")
- `environment`: Environment variables dictionary
- `setup_rc`: Shell RC file to source
- `workdir`: Working directory

#### `ExecuteResult`
Result of command execution.

**Fields:**
- `command`: Command that was executed
- `returncode`: Process exit code
- `stdout`: Standard output
- `stderr`: Standard error
- `execution_time`: Time taken to execute

### Functions

#### `create_shell(shell_type, environment, setup_rc, workdir)`
Create a new shell with configuration.

#### `execute_command(command, timeout, environment, check)`
Execute a single command in a temporary shell.

## Design Decisions

- **No pexpect**: Uses Python's built-in `subprocess` for cross-platform compatibility
- **Async by default**: All command execution is asynchronous
- **Timeout support**: Prevents agent blocking on long-running commands
- **State inheritance**: Forked shells inherit all environment state
- **Context manager support**: Clean resource management with async context managers

## License

MIT
