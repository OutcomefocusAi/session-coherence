"""CLI wrapper — imports and runs chronicle-manager.py main()."""
import importlib.util
import os
import sys


def main():
    # Find chronicle-manager.py relative to this package
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manager_path = os.path.join(pkg_root, "chronicle-manager.py")

    if not os.path.exists(manager_path):
        print(f"Error: chronicle-manager.py not found at {manager_path}", file=sys.stderr)
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("chronicle_manager", manager_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["chronicle_manager"] = mod
    spec.loader.exec_module(mod)

    if hasattr(mod, "main"):
        mod.main()
    else:
        print("Error: chronicle-manager.py has no main() function", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
