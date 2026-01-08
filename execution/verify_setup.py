#!/usr/bin/env python3
"""
Verify AgenticWorkflows setup and dependencies.

Usage:
    python execution/verify_setup.py
"""

import sys
from pathlib import Path


def check_directories():
    """Verify required directories exist."""
    print("Checking directory structure...")
    required = [
        "directives",
        "execution",
        ".tmp",
        ".CLAUDE/agents"
    ]

    all_good = True
    for dir_name in required:
        path = Path(dir_name)
        if path.exists():
            print(f"  [OK] {dir_name}/")
        else:
            print(f"  [MISSING] {dir_name}/")
            all_good = False

    return all_good


def check_files():
    """Verify key files exist."""
    print("\nChecking key files...")
    required = [
        "CLAUDE.md",
        ".env.example",
        ".gitignore",
        "execution/requirements.txt",
        ".CLAUDE/agents/code_reviewer.md",
        ".CLAUDE/agents/directive_updater.md"
    ]

    all_good = True
    for file_name in required:
        path = Path(file_name)
        if path.exists():
            print(f"  [OK] {file_name}")
        else:
            print(f"  [FAIL] {file_name} - MISSING")
            all_good = False

    return all_good


def check_env():
    """Check environment setup."""
    print("\nChecking environment...")

    env_file = Path(".env")
    if env_file.exists():
        print("  [OK] .env file exists")
        return True
    else:
        print("  [WARN] .env file not found")
        print("    Run: cp .env.example .env")
        print("    Then edit .env with your credentials")
        return False


def check_dependencies():
    """Check Python dependencies."""
    print("\nChecking Python dependencies...")

    required = [
        ("requests", "Web requests"),
        ("bs4", "HTML parsing (BeautifulSoup)"),
        ("pandas", "Data processing")
    ]

    optional = [
        ("playwright", "Dynamic content scraping"),
        ("openpyxl", "Excel file support"),
        ("google.auth", "Google API integration"),
        ("modal", "Webhook deployment")
    ]

    all_good = True

    # Check required
    print("  Required:")
    for module, description in required:
        try:
            __import__(module)
            print(f"    [OK] {module} - {description}")
        except ImportError:
            print(f"    [FAIL] {module} - {description} - NOT INSTALLED")
            all_good = False

    # Check optional
    print("  Optional:")
    for module, description in optional:
        try:
            __import__(module)
            print(f"    [OK] {module} - {description}")
        except ImportError:
            print(f"    [WARN] {module} - {description} - not installed")

    if not all_good:
        print("\n  Install missing dependencies:")
        print("    pip install -r execution/requirements.txt")

    return all_good


def check_directives():
    """Verify directives are present."""
    print("\nChecking directives...")

    directive_path = Path("directives")
    if not directive_path.exists():
        print("  [FAIL] directives/ directory missing")
        return False

    directives = list(directive_path.glob("*.md"))
    if directives:
        print(f"  [OK] Found {len(directives)} directive(s):")
        for d in directives:
            print(f"    - {d.name}")
        return True
    else:
        print("  [WARN] No directives found")
        print("    Directives define available workflows")
        return False


def check_scripts():
    """Verify execution scripts are present."""
    print("\nChecking execution scripts...")

    script_path = Path("execution")
    if not script_path.exists():
        print("  [FAIL] execution/ directory missing")
        return False

    scripts = list(script_path.glob("*.py"))
    scripts = [s for s in scripts if s.name != "verify_setup.py"]

    if scripts:
        print(f"  [OK] Found {len(scripts)} script(s):")
        for s in scripts:
            print(f"    - {s.name}")
        return True
    else:
        print("  [WARN] No execution scripts found")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("AgenticWorkflows Setup Verification")
    print("=" * 60)
    print()

    results = []

    results.append(("Directory structure", check_directories()))
    results.append(("Key files", check_files()))
    results.append(("Environment", check_env()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Directives", check_directives()))
    results.append(("Execution scripts", check_scripts()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[OK] PASS" if passed else "[FAIL] FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("SUCCESS: Setup verification complete! System is ready to use.")
        print("\nNext steps:")
        print("  1. Copy .env.example to .env and add your credentials")
        print("  2. Try a simple command: python execution/scrape_single_site.py --help")
        print("  3. Read USAGE_GUIDE.md for examples")
        return 0
    else:
        print("WARNING: Some checks failed. Review the output above.")
        print("\nSetup instructions:")
        print("  1. Install dependencies: pip install -r execution/requirements.txt")
        print("  2. Create .env file: cp .env.example .env")
        print("  3. Run verification again: python execution/verify_setup.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
