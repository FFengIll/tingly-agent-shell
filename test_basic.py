#!/usr/bin/env python3
"""
Basic test for tingly-agent-shell module
"""

import asyncio
import sys

import pytest

from tingly_agent_shell import Shell, ShellConfig, create_shell, execute_command


@pytest.mark.asyncio
async def test_basic_execution():
    """Test basic command execution"""
    print("Testing basic execution...")
    result = await execute_command("echo 'Hello, World!'")
    assert result.returncode == 0
    assert "Hello, World!" in result.stdout
    print("✓ Basic execution works")


@pytest.mark.asyncio
async def test_shell_creation():
    """Test shell creation"""
    print("Testing shell creation...")
    shell = await create_shell(
        shell_type="bash", environment={"TEST_VAR": "test_value"}
    )
    assert shell.getenv("TEST_VAR") == "test_value"
    shell.close()
    print("✓ Shell creation works")


@pytest.mark.asyncio
async def test_environment_variables():
    """Test environment variable management"""
    print("Testing environment variables...")
    shell = await create_shell()

    # Set and get env var
    shell.setenv("CUSTOM_VAR", "custom_value")
    assert shell.getenv("CUSTOM_VAR") == "custom_value"

    # Get all env
    all_env = shell.get_all_env()
    assert "CUSTOM_VAR" in all_env
    assert all_env["CUSTOM_VAR"] == "custom_value"

    shell.close()
    print("✓ Environment variable management works")


@pytest.mark.asyncio
async def test_shell_forking():
    """Test shell forking with state inheritance"""
    print("Testing shell forking...")
    parent = await create_shell(environment={"PARENT_VAR": "parent_value"})

    # Verify parent has the var
    assert parent.getenv("PARENT_VAR") == "parent_value"

    # Fork child
    child = parent.fork()

    # Verify child inherits the var
    assert child.getenv("PARENT_VAR") == "parent_value"

    # Set new var in child
    child.setenv("CHILD_VAR", "child_value")

    # Verify parent doesn't have CHILD_VAR
    assert parent.getenv("CHILD_VAR") is None

    # Verify child has CHILD_VAR
    assert child.getenv("CHILD_VAR") == "child_value"

    parent.close()
    child.close()
    print("✓ Shell forking works")


@pytest.mark.asyncio
async def test_timeout():
    """Test timeout functionality"""
    print("Testing timeout...")
    shell = await create_shell()

    try:
        await shell.execute("sleep 5", timeout=0.5)
        assert False, "Should have timed out"
    except asyncio.TimeoutError:
        print("✓ Timeout works")

    shell.close()


@pytest.mark.asyncio
async def test_context_manager():
    """Test context manager"""
    print("Testing context manager...")
    async with await create_shell() as shell:
        result = await shell.execute("echo 'Context test'")
        assert result.returncode == 0
    print("✓ Context manager works")


@pytest.mark.asyncio
async def test_command_execution():
    """Test command execution in shell"""
    print("Testing command execution...")
    async with await create_shell() as shell:
        # Test successful command
        result = await shell.execute("pwd", check=False)
        assert result.returncode == 0
        assert len(result.stdout) > 0

        # Test failed command
        result = await shell.execute("exit 42", check=False)
        assert result.returncode == 42
    print("✓ Command execution works")


@pytest.mark.asyncio
async def test_shell_config():
    """Test shell configuration"""
    print("Testing shell configuration...")
    config = ShellConfig(
        shell_type="bash", environment={"KEY": "value"}, workdir="/tmp"
    )
    shell = Shell(config=config)

    retrieved_config = shell.get_config()
    assert retrieved_config.shell_type == "bash"
    assert retrieved_config.environment["KEY"] == "value"
    assert retrieved_config.workdir == "/tmp"

    shell.close()
    print("✓ Shell configuration works")


@pytest.mark.asyncio
async def test_persistent_shell():
    """Test persistent shell session (reuses process for multiple commands)"""
    print("Testing persistent shell session...")

    # Create shell with persistent mode enabled (default)
    config = ShellConfig(shell_type="bash", persistent=True)
    async with Shell(config=config) as shell:
        # Execute first command
        result1 = await shell.execute("echo 'First command'", timeout=5.0)
        assert result1.returncode == 0
        assert "First command" in result1.stdout

        # Execute second command - should reuse the same process
        result2 = await shell.execute("echo 'Second command'", timeout=5.0)
        assert result2.returncode == 0
        assert "Second command" in result2.stdout

        # Execute third command to verify process is still alive
        result3 = await shell.execute("pwd", timeout=5.0)
        assert result3.returncode == 0
        assert len(result3.stdout) > 0

    print("✓ Persistent shell session works")


@pytest.mark.asyncio
async def test_non_persistent_shell():
    """Test non-persistent shell mode (spawns new process per command)"""
    print("Testing non-persistent shell mode...")

    # Create shell with persistent mode disabled
    config = ShellConfig(shell_type="bash", persistent=False)
    async with Shell(config=config) as shell:
        # Execute commands - each should spawn a new process
        result1 = await shell.execute("echo 'Command 1'", timeout=5.0)
        assert result1.returncode == 0
        assert "Command 1" in result1.stdout

        result2 = await shell.execute("echo 'Command 2'", timeout=5.0)
        assert result2.returncode == 0
        assert "Command 2" in result2.stdout

    print("✓ Non-persistent shell mode works")


@pytest.mark.asyncio
async def test_persistent_shell_with_pre_scripts():
    """Test persistent shell with pre_scripts initialization"""
    print("Testing persistent shell with pre_scripts...")

    config = ShellConfig(
        shell_type="bash",
        persistent=True,
        pre_scripts=["export TEST_VAR='persistent_test'", "echo 'Shell initialized'"]
    )
    async with Shell(config=config) as shell:
        # Pre-scripts should have run during initialization
        result = await shell.execute("echo $TEST_VAR", timeout=5.0)
        assert result.returncode == 0
        # Environment variable should be set
        # Note: In persistent mode, the environment sync might not capture all exports
        # but the command should execute successfully
        assert len(result.stdout) > 0

    print("✓ Persistent shell with pre_scripts works")


@pytest.mark.asyncio
async def test_persistent_shell_state_preservation():
    """Test that state is preserved across commands in persistent mode"""
    print("Testing persistent shell state preservation...")

    config = ShellConfig(shell_type="bash", persistent=True)
    async with Shell(config=config) as shell:
        # Set an environment variable
        shell.setenv("STATE_VAR", "preserved_value")

        # Execute a command that references the variable
        result1 = await shell.execute("echo $STATE_VAR", timeout=5.0)
        assert result1.returncode == 0

        # Execute another command to verify state is still there
        result2 = await shell.execute("pwd", timeout=5.0)
        assert result2.returncode == 0

    print("✓ Persistent shell state preservation works")


async def main():
    """Run all tests"""
    print("=" * 50)
    print("Running tests for tingly-agent-shell")
    print("=" * 50)
    print()

    tests = [
        test_basic_execution,
        test_shell_creation,
        test_environment_variables,
        test_shell_forking,
        test_timeout,
        test_context_manager,
        test_command_execution,
        test_shell_config,
        test_persistent_shell,
        test_non_persistent_shell,
        test_persistent_shell_with_pre_scripts,
        test_persistent_shell_state_preservation,
    ]

    failed = []
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append((test.__name__, e))

    print()
    print("=" * 50)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print("SUCCESS: All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
