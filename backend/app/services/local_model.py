"""Opt-in startup of an already installed Ollama on the local Windows machine."""

import asyncio
import logging
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)
IS_WINDOWS = os.name == "nt"


async def ensure_local_model_server():
    settings = get_settings()
    if not settings.ollama_auto_start or not IS_WINDOWS:
        return False
    target = urlparse(settings.ollama_base_url)
    if (
        target.scheme != "http"
        or target.hostname not in {"127.0.0.1", "localhost", "::1"}
        or target.username
        or target.password
        or target.path not in {"", "/"}
        or target.query
        or target.fragment
    ):
        logger.warning("Ollama auto-start only supports an HTTP loopback endpoint.")
        return False
    try:
        port = target.port or 11434
    except ValueError:
        return False
    async with httpx.AsyncClient(
        base_url=settings.ollama_base_url.rstrip("/"), timeout=2, trust_env=False
    ) as client:

        async def ready():
            try:
                response = await client.get("/api/tags")
                return response.status_code == 200 and isinstance(
                    response.json().get("models"), list
                )
            except (httpx.HTTPError, ValueError, AttributeError):
                return False

        if await ready():
            return True
        local_data = os.environ.get("LOCALAPPDATA")
        portable = Path(local_data) / "AITrade" / "ollama" / "ollama.exe" if local_data else None
        executable = shutil.which("ollama")
        use_portable = not executable and portable is not None and portable.is_file()
        if use_portable:
            executable = str(portable)
        if not executable:
            logger.warning(
                "Ollama is not installed. Run scripts/Start-AICoach.ps1 after installing Ollama."
            )
            return False
        environment = os.environ.copy()
        environment["OLLAMA_HOST"] = (
            f"127.0.0.1:{port}" if target.hostname != "::1" else f"[::1]:{port}"
        )
        if use_portable:
            environment["OLLAMA_MODELS"] = str(portable.parent.parent / "models")
        try:
            logs = Path(__file__).resolve().parents[2] / "logs"
            logs.mkdir(exist_ok=True)
            with (logs / "ollama-startup.log").open("ab") as log:
                subprocess.Popen(
                    [executable, "serve"],
                    env=environment,
                    stdout=log,
                    stderr=log,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            for _ in range(20):
                await asyncio.sleep(0.5)
                if await ready():
                    logger.info("Local Ollama server is ready.")
                    return True
        except OSError:
            logger.warning(
                "Could not start the installed local Ollama server; see the setup guide."
            )
        logger.warning(
            "Ollama startup did not complete; chat will report an unavailable model server."
        )
        return False
