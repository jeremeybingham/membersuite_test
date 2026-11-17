"""Credentials and settings, read from the environment or a git-ignored `.env` file.

Copy `.env.example` to `.env` and fill it in. Nothing here is ever written to disk or printed.
If `MS_PASSWORD` is not set, the CLI asks for it at the prompt instead.
"""

import getpass
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://rest.membersuite.com"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "local-data"


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    tenant_id: int
    username: str
    password: str
    base_url: str = DEFAULT_BASE_URL

    def __repr__(self) -> str:  # never show the password in tracebacks or logs
        return f"Settings(tenant_id={self.tenant_id}, username=***, base_url={self.base_url!r})"


def load_settings(env_file: Path | None = None, prompt: bool = True) -> Settings:
    load_dotenv(env_file or REPO_ROOT / ".env", override=False)
    tenant = os.environ.get("MS_TENANT_ID", "").strip()
    username = os.environ.get("MS_USERNAME", "").strip()
    password = os.environ.get("MS_PASSWORD", "")
    missing = [n for n, v in (("MS_TENANT_ID", tenant), ("MS_USERNAME", username)) if not v]
    if missing:
        raise ConfigError(f"missing {', '.join(missing)}: copy .env.example to .env and fill it in")
    if not tenant.isdigit():
        raise ConfigError("MS_TENANT_ID must be the numeric association (tenant) id")
    if not password:
        if not prompt:
            raise ConfigError("missing MS_PASSWORD")
        password = getpass.getpass(f"MemberSuite password for {username}: ")
    base_url = os.environ.get("MS_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    return Settings(int(tenant), username, password, base_url)
