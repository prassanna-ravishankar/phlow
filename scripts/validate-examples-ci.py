#!/usr/bin/env python3
"""
CI-safe example validation script.
Tests examples without external dependencies.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path


def log_success(msg):
    print(f"✅ {msg}")


def log_error(msg):
    print(f"❌ {msg}")


def log_info(msg):
    print(f"ℹ️ {msg}")


def validate_example(example_dir: Path, example_name: str) -> bool:
    """Validate a single example directory."""
    log_info(f"📂 Validating {example_name} example...")

    # Check required files exist
    required_files = ["README.md", "main.py", "requirements.txt"]
    for file in required_files:
        if not (example_dir / file).exists():
            log_error(f"Missing {file}")
            return False
    log_success("Required files present")

    # Check Python syntax
    try:
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(example_dir / "main.py")],
            check=True,
            capture_output=True,
        )
        log_success("Python syntax valid")
    except subprocess.CalledProcessError:
        log_error("Python syntax error in main.py")
        return False

    # Check dependencies can be resolved
    try:
        subprocess.run(
            ["uv", "pip", "compile", str(example_dir / "requirements.txt"), "--quiet"],
            check=True,
            capture_output=True,
            cwd=example_dir,
        )
        log_success("Dependencies can be resolved")
    except subprocess.CalledProcessError:
        log_error("Dependencies cannot be resolved")
        return False

    # Test module imports and structure
    sys.path.insert(0, str(example_dir))
    try:
        spec = importlib.util.spec_from_file_location("main", example_dir / "main.py")
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        log_success("Main module imports successfully")

        # Check FastAPI app exists
        if not hasattr(main_module, "app"):
            log_error("No FastAPI app found")
            return False
        log_success("FastAPI app found")

        # Check A2A endpoints exist
        app = main_module.app
        routes = [route.path for route in app.routes if hasattr(route, "path")]
        required_routes = ["/.well-known/agent.json", "/tasks/send"]

        for route in required_routes:
            if route not in routes:
                log_error(f"Missing A2A endpoint: {route}")
                return False
            log_success(f"A2A endpoint {route} found")

        # Test agent card endpoint
        try:
            agent_card = main_module.agent_card()
            required_fields = ["id", "name", "description", "capabilities", "endpoints"]

            for field in required_fields:
                if field not in agent_card:
                    log_error(f"Missing required field in agent card: {field}")
                    return False

            if agent_card["endpoints"].get("task") != "/tasks/send":
                log_error("Incorrect task endpoint in agent card")
                return False

            log_success("Agent card structure valid")
        except Exception as e:
            log_error(f"Agent card test failed: {e}")
            return False

        # Test task endpoint
        try:
            test_task = {
                "id": "test-123",
                "message": {"parts": [{"type": "text", "text": "Hello test"}]},
            }

            response = main_module.send_task(test_task)

            # Validate A2A response structure
            required_fields = ["id", "status", "messages", "metadata"]
            for field in required_fields:
                if field not in response:
                    log_error(f"Missing required field in task response: {field}")
                    return False

            if response["status"]["state"] not in ["completed", "failed"]:
                log_error("Invalid status state in task response")
                return False

            if not response["messages"] or not isinstance(response["messages"], list):
                log_error("Invalid messages structure in task response")
                return False

            log_success("Task endpoint structure valid")
        except Exception as e:
            log_error(f"Task endpoint test failed: {e}")
            return False

    except Exception as e:
        log_error(f"Import/structure validation failed: {e}")
        return False
    finally:
        sys.path.remove(str(example_dir))

    log_success(f"{example_name} example validation complete")
    return True


def main():
    """Main validation function."""
    log_info("🔍 Validating example structure and functionality...")

    # Find examples directory
    examples_dir = Path("examples")
    if not examples_dir.exists():
        log_error("Examples directory not found")
        return 1

    # Validate each example
    examples = [
        ("simple", "Simple Agent"),
        ("multi-agent", "Multi-Agent"),
        ("rbac_agent", "RBAC Agent"),
    ]

    all_passed = True
    for example_dir_name, example_name in examples:
        example_dir = examples_dir / example_dir_name
        if not example_dir.exists():
            log_error(f"Example directory {example_dir_name} not found")
            all_passed = False
            continue

        if not validate_example(example_dir, example_name):
            all_passed = False
        print()  # Add spacing between examples

    if all_passed:
        log_success("🎉 All examples validated successfully!")
        return 0
    else:
        log_error("❌ Some examples failed validation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
