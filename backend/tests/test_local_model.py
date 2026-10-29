from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import httpx
from app.services import local_model


async def test_auto_start_is_opt_in_and_never_starts_remote_servers():
    for enabled, url in [
        (False, "http://127.0.0.1:11434"),
        (True, "https://server.example"),
        (True, "http://127.0.0.1:11434/other"),
    ]:
        settings = SimpleNamespace(ollama_auto_start=enabled, ollama_base_url=url)
        with (
            patch.object(local_model, "get_settings", return_value=settings),
            patch.object(local_model, "IS_WINDOWS", True),
            patch.object(local_model.subprocess, "Popen") as launch,
        ):
            assert not await local_model.ensure_local_model_server()
            launch.assert_not_called()


async def test_existing_server_is_reused_without_launch_or_download():
    settings = SimpleNamespace(ollama_auto_start=True, ollama_base_url="http://127.0.0.1:11434")
    real = httpx.AsyncClient

    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": []})

    with (
        patch.object(local_model, "get_settings", return_value=settings),
        patch.object(local_model, "IS_WINDOWS", True),
        patch.object(
            local_model.httpx,
            "AsyncClient",
            side_effect=lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
        ),
        patch.object(local_model.subprocess, "Popen") as launch,
    ):
        assert await local_model.ensure_local_model_server()
        launch.assert_not_called()


async def test_portable_runtime_starts_loopback_with_its_existing_models(tmp_path, monkeypatch):
    executable = tmp_path / "AITrade" / "ollama" / "ollama.exe"
    executable.parent.mkdir(parents=True)
    executable.write_text("fixture only; never executed")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    settings = SimpleNamespace(ollama_auto_start=True, ollama_base_url="http://127.0.0.1:11434")
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("fixture offline", request=request)
        return httpx.Response(200, json={"models": []})

    real = httpx.AsyncClient
    with (
        patch.object(local_model, "get_settings", return_value=settings),
        patch.object(local_model, "IS_WINDOWS", True),
        patch.object(
            local_model.httpx,
            "AsyncClient",
            side_effect=lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
        ),
        patch.object(local_model.shutil, "which", return_value=None),
        patch.object(local_model.subprocess, "Popen") as launch,
        patch.object(local_model.asyncio, "sleep", new=AsyncMock()),
    ):
        assert await local_model.ensure_local_model_server()
        assert launch.call_args.args[0] == [str(executable), "serve"]
        env = launch.call_args.kwargs["env"]
        assert env["OLLAMA_HOST"] == "127.0.0.1:11434"
        assert env["OLLAMA_MODELS"] == str(tmp_path / "AITrade" / "models")
