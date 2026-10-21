"""Source-checkout shortcut: `python remote/ask_mydesk.py …` == `mydesk ask …`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mydesk.remote import ask, main  # noqa: E402,F401

if __name__ == "__main__":
    main()
