#!/usr/bin/env python3
"""
Basic usage example for tingly-agent-shell
"""

import asyncio
from tingly_agent_shell import create_shell, execute_command


async def example_1_basic_execution():
    """Example 1: Execute a simple command"""
    print("=== Example 1: Basic Command Execution ===")
    result = await execute_command("echo 'Hello, World!'")
    print(f"Output: {result.stdout}")
    print(f"Exit code: {result.returncode}")
    print()


async def example_2_shell_with_env():
    """Example 2: Create shell with custom environment"""
    print("=== Example 2: Shell with Custom Environment ===")
    shell = await create_shell(
        environment={"MY_VAR": "my_value", "APP_NAME": "TinglyAgent"}
    )

    result = await shell.execute("echo $MY_VAR $APP_NAME")
    print(f"Output: {result.stdout}")

    shell.close()
    print()


async def example_3_shell_forking():
    """Example 3: Fork shell with state inheritance"""
    print("=== Example 3: Shell Forking and State Inheritance ===")
    parent = await create_shell(environment={"PARENT_VAR": "parent_value"})

    # Execute in parent
    result = await parent.execute("echo Parent: $PARENT_VAR")
    print(result.stdout)

    # Fork child shell
    child = parent.fork()

    # Execute in child - should have access to PARENT_VAR
    result = await child.execute("echo Child: $PARENT_VAR")
    print(result.stdout)

    # Set new variable in child
    child.setenv("CHILD_VAR", "child_value")

    # Verify parent doesn't have CHILD_VAR
    result = await parent.execute("echo Parent CHILD_VAR: $CHILD_VAR")
    print(result.stdout)

    # Verify child has CHILD_VAR
    result = await child.execute("echo Child CHILD_VAR: $CHILD_VAR")
    print(result.stdout)

    parent.close()
    child.close()
    print()


async def example_4_context_manager():
    """Example 4: Using context manager for automatic cleanup"""
    print("=== Example 4: Context Manager ===")
    async with await create_shell() as shell:
        result = await shell.execute("pwd")
        print(f"Current directory: {result.stdout.strip()}")

        result = await shell.execute("whoami")
        print(f"Current user: {result.stdout.strip()}")
    print()


async def example_5_timeout():
    """Example 5: Command timeout handling"""
    print("=== Example 5: Timeout Handling ===")
    shell = await create_shell()

    try:
        # This command will timeout
        result = await shell.execute("sleep 3", timeout=1.0)
        print("Command completed (this shouldn't happen)")
    except asyncio.TimeoutError:
        print("Command timed out as expected!")

    shell.close()
    print()


async def example_6_error_handling():
    """Example 6: Error handling and exit codes"""
    print("=== Example 6: Error Handling ===")
    shell = await create_shell()

    # Execute a command that fails
    result = await shell.execute("ls /nonexistent", check=False)
    print(f"Exit code: {result.returncode}")
    print(f"Error: {result.stderr.strip()}")

    shell.close()
    print()


async def example_7_command_state():
    """Example 7: Commands maintain state"""
    print("=== Example 7: Command State Persistence ===")
    async with await create_shell(shell_type="bash") as shell:
        # Set a variable
        await shell.execute("export MY_VAR='Hello from shell'")
        # Use it in next command
        result = await shell.execute("echo $MY_VAR")
        print(f"Output: {result.stdout.strip()}")
    print()


async def main():
    """Run all examples"""
    print("Tingly Agent Shell - Basic Usage Examples\n")

    await example_1_basic_execution()
    await example_2_shell_with_env()
    await example_3_shell_forking()
    await example_4_context_manager()
    await example_5_timeout()
    await example_6_error_handling()
    await example_7_command_state()

    print("All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
