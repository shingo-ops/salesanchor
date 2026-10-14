"""依存関数が request.state に入れた値を、応答後の middleware が読めること（starlette 1.3.1）。"""
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware


def test_state_set_in_dependency_visible_to_middleware():
    app = FastAPI()
    seen = {}

    async def dep(request: Request):
        request.state.rt_tenant_id = "7"
        return 1

    class MW(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            resp = await call_next(request)
            seen["tenant"] = getattr(request.state, "rt_tenant_id", None)
            seen["route"] = getattr(request.scope.get("route"), "path", None)
            return resp

    @app.post("/x/{i}")
    async def h(i: int, _=Depends(dep)):
        return {"ok": True}

    app.add_middleware(MW)
    r = TestClient(app).post("/x/1")
    assert r.status_code == 200
    assert seen["tenant"] == "7"
    assert seen["route"] == "/x/{i}"
