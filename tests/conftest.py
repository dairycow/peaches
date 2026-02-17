"""Test configuration fixtures."""

import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

os.environ["COOLTRADER_USERNAME"] = "test"
os.environ["COOLTRADER_PASSWORD"] = "test"
