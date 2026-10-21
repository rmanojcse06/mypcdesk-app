"""Source-checkout shortcut: `python pc_status.py` == `mydesk status`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mydesk.status import main  # noqa: E402

if __name__ == "__main__":
    main()
