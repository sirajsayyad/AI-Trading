import warnings
from collections import Counter

from app.main import create_app


def test_api_routes_and_operation_ids_are_unique():
    app = create_app()
    routes = [
        (method, route.path) for route in app.routes for method in getattr(route, "methods", [])
    ]
    assert all(count == 1 for count in Counter(routes).values())
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        schema = app.openapi()
    assert "/courses" in schema["paths"]
    assert "/courses/{course_id}" in schema["paths"]
    assert "/lessons/{lesson_id}" in schema["paths"]


async def test_local_frontend_preflight():
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        for origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
            response = await client.options(
                "/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin
