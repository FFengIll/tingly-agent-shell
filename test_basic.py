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
