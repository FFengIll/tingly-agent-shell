#!/usr/bin/env python3
"""
Test environment variable tracking and setup_rc features
"""

import asyncio

import pytest

from tingly_agent_shell import create_shell


@pytest.mark.asyncio
async def test_env_var_tracking():
    """Test that environment variables set via export are tracked"""
    print("Testing environment variable tracking...")
    shell = await create_shell()

    # Set an environment variable using export
    await shell.execute("export MY_VAR='test_value'")
    print(f"MY_VAR after export: {shell.getenv('MY_VAR')}")
    assert shell.getenv("MY_VAR") == "test_value", "MY_VAR should be tracked"

    # Change the variable
    await shell.execute("export MY_VAR='updated_value'")
    print(f"MY_VAR after update: {shell.getenv('MY_VAR')}")
    assert shell.getenv("MY_VAR") == "updated_value", "MY_VAR should be updated"

    # Set PATH variable
    await shell.execute("export PATH='/custom/path:$PATH'")
    path = shell.getenv("PATH")
    print(f"PATH after modification: {path}")
    assert "/custom/path" in path, "PATH should include custom path"

    shell.close()
    print("✓ Environment variable tracking works\n")


@pytest.mark.asyncio
async def test_setup_rc():
    """Test that setup_rc commands are executed"""
    print("Testing setup_rc...")

    # Create shell with setup commands
    shell = await create_shell(
        pre_scripts=["export SETUP_VAR='initialized'", "export ANOTHER_VAR='42'"]
    )

    # Check if setup variables are set
    assert shell.getenv("SETUP_VAR") == "initialized", "SETUP_VAR should be initialized"
    print(f"SETUP_VAR: {shell.getenv('SETUP_VAR')}")

    assert shell.getenv("ANOTHER_VAR") == "42", "ANOTHER_VAR should be initialized"
    print(f"ANOTHER_VAR: {shell.getenv('ANOTHER_VAR')}")

    shell.close()
    print("✓ setup_rc works\n")


@pytest.mark.asyncio
async def test_fork_inherits_env():
    """Test that forked shell inherits environment changes"""
    print("Testing fork inherits environment changes...")

    parent = await create_shell()

    # Set variable in parent
    await parent.execute("export PARENT_VAR='parent_value'")
    print(f"Parent PARENT_VAR: {parent.getenv('PARENT_VAR')}")

    # Fork child
    child = parent.fork()

    # Check child has the variable
    assert (
        child.getenv("PARENT_VAR") == "parent_value"
    ), "Child should inherit PARENT_VAR"
    print(f"Child PARENT_VAR: {child.getenv('PARENT_VAR')}")

    # Set variable in child
    await child.execute("export CHILD_VAR='child_value'")
    print(f"Child CHILD_VAR: {child.getenv('CHILD_VAR')}")

    # Verify parent doesn't have CHILD_VAR
    assert parent.getenv("CHILD_VAR") is None, "Parent should not have CHILD_VAR"
    print(f"Parent CHILD_VAR: {parent.getenv('CHILD_VAR')}")

    # But child should still have PARENT_VAR
    assert (
        child.getenv("PARENT_VAR") == "parent_value"
    ), "Child should still have PARENT_VAR"

    parent.close()
    child.close()
    print("✓ Fork inherits environment changes\n")


@pytest.mark.asyncio
async def test_multiple_setup_commands():
    """Test multiple setup commands execute in order"""
    print("Testing multiple setup commands...")

    shell = await create_shell(
        pre_scripts=[
            "export VAR1='value1'",
            "export VAR2='$VAR1-value2'",
            "export VAR3='$VAR1-$VAR2'",
        ]
    )

    # Verify all variables are set correctly
    assert shell.getenv("VAR1") == "value1"
    assert shell.getenv("VAR2") == "value1-value2"
    assert shell.getenv("VAR3") == "value1-value1-value2"

    print(f"VAR1: {shell.getenv('VAR1')}")
    print(f"VAR2: {shell.getenv('VAR2')}")
    print(f"VAR3: {shell.getenv('VAR3')}")

    shell.close()
    print("✓ Multiple setup commands work\n")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Environment Variable Tracking and setup_rc")
    print("=" * 60)
    print()

    tests = [
        test_env_var_tracking,
        test_setup_rc,
        test_fork_inherits_env,
        test_multiple_setup_commands,
    ]

    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback

            traceback.print_exc()
            return 1

    print("=" * 60)
    print("SUCCESS: All tests passed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
