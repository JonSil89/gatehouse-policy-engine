import sys


def read_change_request(file_path):
    """Read a change request file using relative path."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: Change request file not found: {file_path}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: Could not read file: {e}", file=sys.stderr)
        sys.exit(2)
