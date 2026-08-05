from __future__ import annotations

import os

os.environ["OPSFORGE_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OPSFORGE_ENVIRONMENT"] = "test"
