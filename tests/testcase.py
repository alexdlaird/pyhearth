__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import unittest
from typing import Any

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from pyhearth.client import HearthClient


class HearthTestCase(unittest.IsolatedAsyncioTestCase):
    API_KEY = "test-hearth-api-key"

    async def asyncSetUp(self) -> None:
        self.answers: dict[str, tuple[int, str, dict[str, str]]] = {}
        self.posts: dict[str, list[Any]] = {}
        self.authorizations: list[str | None] = []

        app = web.Application()
        app.router.add_post("/v1/{endpoint}", self._answer)
        self.server = TestServer(app)
        await self.server.start_server()
        self.session = aiohttp.ClientSession()

    async def asyncTearDown(self) -> None:
        await self.session.close()
        await self.server.close()

    def given_client(self, **options: Any) -> HearthClient:
        return HearthClient(self.session, self.API_KEY, str(self.server.make_url("/")), **options)

    def given_hearth_answers(self,
                             endpoint: str,
                             status: int = 200,
                             body: str = "",
                             headers: dict[str, str] | None = None) -> None:
        self.answers[endpoint] = (status, body, headers or {})

    def posted(self, endpoint: str) -> list[Any]:
        return self.posts.get(endpoint, [])

    async def _answer(self, request: web.Request) -> web.Response:
        endpoint = request.match_info["endpoint"]
        self.posts.setdefault(endpoint, []).append(await request.json())
        self.authorizations.append(request.headers.get("Authorization"))
        status, body, headers = self.answers.get(endpoint, (204, "", {}))
        return web.Response(status=status, text=body, headers=headers)
