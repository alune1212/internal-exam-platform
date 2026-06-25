import asyncio

from fastapi.testclient import TestClient

from app import main


def test_api_lifespan_does_not_start_auto_submit_loop(
    monkeypatch,
) -> None:
    started: list[bool] = []

    async def fake_auto_submit_loop() -> None:
        started.append(True)
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "auto_submit_loop", fake_auto_submit_loop, raising=False)
    app = main.create_app()

    with TestClient(app):
        pass

    assert started == []
