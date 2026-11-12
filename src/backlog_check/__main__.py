"""Allow ``python -m backlog_check``."""

import sys

from .cli import main

sys.exit(main())
