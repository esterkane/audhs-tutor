from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import AppError
from app.main import create_app


async def test_notebook_link_revalidates_every_navigation_without_caching() -> None:
    app = create_app(Settings(auto_migrate=False, _env_file=None))  # type: ignore[call-arg]
    service, command = str(uuid4()), str(uuid4())
    target = "http://127.0.0.1:8899/lab/tree/lesson.ipynb?token=fixture"
    launch = AsyncMock(side_effect=[target, AppError("notebook_unavailable", "Gone", 409)])
    app.state.notebook_lab.launch_url = launch
    path = f"/api/notebooks/open/{service}/{command}"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", follow_redirects=False
    ) as client:
        denied = await client.get(path, headers={"Origin": "https://example.com"})
        assert denied.status_code == 403
        for site in ("cross-site", "same-site"):
            denied = await client.get(
                path, headers={"sec-fetch-site": site, "sec-fetch-mode": "navigate"}
            )
            assert denied.status_code == 403 and "location" not in denied.headers
            assert denied.headers["cache-control"] == "no-store"
        launch.assert_not_called()
        good = await client.get(path, headers={"sec-fetch-site": "same-origin"})
        assert good.status_code == 303
        assert good.headers["location"] == target
        gone = await client.get(path)
        assert gone.status_code == 409 and "location" not in gone.headers
        assert "token" not in gone.text and "prepare" in gone.text
        for response in (good, gone):
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["referrer-policy"] == "no-referrer"
    assert launch.await_count == 2
    launch.assert_awaited_with(service, command)
