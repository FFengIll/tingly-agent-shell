#!/usr/bin/env python3
"""
Advanced examples demonstrating environment variable tracking and setup_rc
"""

import asyncio
from tingly_agent_shell import create_shell


async def example_env_tracking():
    """Example: Environment variable tracking from export commands"""
    print("=== Example 1: Environment Variable Tracking ===")

    shell = await create_shell()

    # Set a variable using export
    print("1. Setting MY_VAR via export...")
    await shell.execute("export MY_VAR='hello_world'")
    print(f"   Tracked value: {shell.getenv('MY_VAR')}")

    # Update the variable
    print("\n2. Updating MY_VAR...")
    await shell.execute("export MY_VAR='updated_value'")
    print(f"   Tracked value: {shell.getenv('MY_VAR')}")

    # Set PATH with variable expansion
    print("\n3. Modifying PATH...")
    await shell.execute("export PATH='/custom/bin:$PATH'")
    path = shell.getenv('PATH')
    print(f"   PATH starts with: {path[:50]}...")

    shell.close()
    print()


async def example_setup_rc_multiple():
    """Example: Multiple setup commands with variable expansion"""
    print("=== Example 2: Multiple Setup Commands ===")

    # Create shell with multiple setup commands
    shell = await create_shell(
        setup_rc=[
            "export BASE_DIR='/tmp/myapp'",
            "export CONFIG_FILE='$BASE_DIR/config.yaml'",
            "export DATA_DIR='$BASE_DIR/data'",
            "export LOG_FILE='$DATA_DIR/app.log'"
        ]
    )

    print("Setup variables from config:")
    print(f"  BASE_DIR: {shell.getenv('BASE_DIR')}")
    print(f"  CONFIG_FILE: {shell.getenv('CONFIG_FILE')}")
    print(f"  DATA_DIR: {shell.getenv('DATA_DIR')}")
    print(f"  LOG_FILE: {shell.getenv('LOG_FILE')}")

    shell.close()
    print()


async def example_fork_with_env_changes():
    """Example: Forking preserves environment changes"""
    print("=== Example 3: Fork with Environment Changes ===")

    parent = await create_shell()

    # Set up environment in parent
    print("1. Parent setting up environment...")
    await parent.execute("export PARENT_VAR='from_parent'")
    await parent.execute("export SHARED_RESOURCE='/shared/data'")

    # Fork child
    print("\n2. Creating child shell...")
    child = parent.fork()

    # Check child has inherited variables
    print(f"   Child has PARENT_VAR: {child.getenv('PARENT_VAR')}")
    print(f"   Child has SHARED_RESOURCE: {child.getenv('SHARED_RESOURCE')}")

    # Modify child's environment
    print("\n3. Child modifying its environment...")
    await child.execute("export CHILD_VAR='only_in_child'")
    await child.execute("export SHARED_RESOURCE='/child/override'")

    # Verify isolation
    print(f"\n4. Verifying isolation:")
    print(f"   Parent SHARED_RESOURCE: {parent.getenv('SHARED_RESOURCE')}")
    print(f"   Child SHARED_RESOURCE: {child.getenv('SHARED_RESOURCE')}")
    print(f"   Parent CHILD_VAR: {parent.getenv('CHILD_VAR')}")
    print(f"   Child CHILD_VAR: {child.getenv('CHILD_VAR')}")

    parent.close()
    child.close()
    print()


async def example_complex_setup():
    """Example: Complex setup with conditional logic"""
    print("=== Example 4: Complex Setup Scenario ===")

    # Simulate a development environment setup
    shell = await create_shell(
        setup_rc=[
            "export ENV='development'",
            "export DEBUG='true'",
            "export LOG_LEVEL='debug'",
            "export DB_HOST='localhost'",
            "export DB_PORT='5432'",
            "export DB_NAME='myapp_dev'"
        ]
    )

    print("Development environment configured:")
    for key in ['ENV', 'DEBUG', 'LOG_LEVEL', 'DB_HOST', 'DB_PORT', 'DB_NAME']:
        print(f"  {key}={shell.getenv(key)}")

    # Fork production environment
    print("\nCreating production fork...")
    prod = shell.fork()

    # Update production settings
    await prod.execute("export ENV='production'")
    await prod.execute("export DEBUG='false'")
    await prod.execute("export LOG_LEVEL='error'")
    await prod.execute("export DB_HOST='prod.db.example.com'")

    print("Production environment:")
    for key in ['ENV', 'DEBUG', 'LOG_LEVEL', 'DB_HOST', 'DB_PORT', 'DB_NAME']:
        print(f"  {key}={prod.getenv(key)}")

    print("\nDevelopment environment (unchanged):")
    for key in ['ENV', 'DEBUG', 'LOG_LEVEL', 'DB_HOST', 'DB_PORT', 'DB_NAME']:
        print(f"  {key}={shell.getenv(key)}")

    shell.close()
    prod.close()
    print()


async def example_tracking_disabled():
    """Example: Disabling environment sync for performance"""
    print("=== Example 5: Disabling Environment Sync ===")

    shell = await create_shell()

    # Execute without tracking environment
    print("1. Executing without env tracking...")
    result = await shell.execute(
        "export NO_TRACK='should_not_appear'",
        sync_env=False
    )
    print(f"   Variable tracked: {shell.getenv('NO_TRACK')}")

    # Execute with tracking
    print("\n2. Executing with env tracking...")
    result = await shell.execute(
        "export TRACKED='will_appear'",
        sync_env=True
    )
    print(f"   Variable tracked: {shell.getenv('TRACKED')}")

    shell.close()
    print()


async def main():
    """Run all advanced examples"""
    print("Tingly Agent Shell - Advanced Features Examples\n")
    print("=" * 60)
    print()

    examples = [
        example_env_tracking,
        example_setup_rc_multiple,
        example_fork_with_env_changes,
        example_complex_setup,
        example_tracking_disabled,
    ]

    for example in examples:
        try:
            await example()
            await asyncio.sleep(0.1)  # Small delay between examples
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print("All advanced examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
