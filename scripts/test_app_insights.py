#!/usr/bin/env python3
"""
Test script to verify Application Insights configuration for all services.
"""

import os
import sys
import logging
from pathlib import Path


def test_app_insights_env():
    """Test if Application Insights environment variables are set."""
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not connection_string:
        print("❌ APPLICATIONINSIGHTS_CONNECTION_STRING not found in environment")
        return False

    if not connection_string.startswith("InstrumentationKey="):
        print(
            f"❌ Invalid Application Insights connection string format: {connection_string[:50]}...")
        return False

    print(
        f"✅ Application Insights connection string found: {connection_string[:50]}...")
    return True


def test_python_dependencies():
    """Test if required Python packages are available."""
    packages = [
        "azure.monitor.opentelemetry",
        "opentelemetry.sdk",
        "opentelemetry.instrumentation.httpx",
        "opentelemetry.instrumentation.fastapi"
    ]

    missing_packages = []
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} not available")
            missing_packages.append(package)

    return len(missing_packages) == 0


def test_service_configuration():
    """Test Application Insights configuration in service files."""
    services = [
        ("setlist-agent", "src/setlist-agent/main.py"),
        ("spotify-mcp-server", "src/spotify-mcp-server/spotify.py"),
        ("setlistfm-mcp-server", "src/setlistfm-mcp-server/setlistfm.py")
    ]

    all_configured = True
    for service_name, file_path in services:
        full_path = Path(__file__).parent.parent / file_path

        if not full_path.exists():
            print(f"❌ {service_name}: File {file_path} not found")
            all_configured = False
            continue

        with open(full_path, 'r') as f:
            content = f.read()

        if "configure_azure_monitor" in content:
            print(f"✅ {service_name}: Application Insights configured")
        else:
            print(f"❌ {service_name}: Application Insights not configured")
            all_configured = False

    return all_configured


def main():
    """Main test function."""
    print("🧪 Testing Application Insights Configuration\n")

    tests = [
        ("Environment Variables", test_app_insights_env),
        ("Python Dependencies", test_python_dependencies),
        ("Service Configuration", test_service_configuration)
    ]

    all_passed = True
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        try:
            result = test_func()
            all_passed = all_passed and result
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            all_passed = False

    print("\n" + "="*50)
    if all_passed:
        print("🎉 All Application Insights tests passed!")
        return 0
    else:
        print("❌ Some Application Insights tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
