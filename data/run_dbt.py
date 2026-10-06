"""Run dbt with variables from the repo's .env file.

Usage (from repo root):
    uv run --project data python data/run_dbt.py debug
    uv run --project data python data/run_dbt.py build --select staging
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from dbt.cli.main import dbtRunner

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = Path(__file__).resolve().parent / "dbt"
# override=True: values in .env win over any variable already set in Windows
load_dotenv(os.getenv("QP_ENV_FILE") or ROOT / ".env", override=True)
os.chdir(DBT_DIR)  # dbt finds dbt_project.yml and profiles.yml here
result = dbtRunner().invoke(sys.argv[1:])
sys.exit(0 if result.success else 1)