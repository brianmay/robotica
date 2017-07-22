import asyncio
import base64
import datetime
import logging
import yaml

from aiohttp import web
from typing import Any, Awaitable, Callable, Union

from robotica import __version__ as version
from robotica.schedule import Schedule

logger = logging.getLogger(__name__)

JsonType = Any
Handler = Callable[[int], Awaitable[JsonType]]


class Http:
    def __init__(
            self, loop: asyncio.AbstractEventLoop,
            config: Union[None, str],
            schedule: Schedule) -> None:
        self._loop = loop
        if config is not None:
            with open(config, "r") as file:
                self._config = yaml.safe_load(file)
            self._disabled = self._config['disabled']
            self._username = self._config['username']
            self._password = self._config['password']
            self._schedule = schedule
        else:
            self._disabled = True

    @staticmethod
    def _get_version(request: web.Request) -> JsonType:
        return {
            'version': version,
        }

    def _get_schedule(self, request: web.Request) -> JsonType:
        try:
            date = request.match_info['date']
            year, month, day = [int(str) for str in date.split("-")]
            parsed_date = datetime.date(year=year, month=month, day=day)
        except ValueError:
            raise web.HTTPBadRequest()
        schedule = self._schedule.get_schedule_for_date(parsed_date)
        return [s.to_json() for s in schedule]

    def _get_application(self) -> web.Application:
        """ Setup router to point to our handlers. """
        app = web.Application(middlewares=[self._authorize, self._rest])
        app.router.add_get('/version/', self._get_version)

        schedule = app.router.add_resource('/schedule/{date}/')
        schedule.add_route('GET', self._get_schedule)
        return app

    def start(self) -> None:
        if not self._disabled:
            self._app = self._get_application()
            self._handler = self._app.make_handler()
            f = self._loop.create_server(self._handler, '0.0.0.0', 8080)
            self._srv = self._loop.run_until_complete(f)
            logger.info('serving on %s', self._srv.sockets[0].getsockname())

    def stop(self) -> None:
        if not self._disabled:
            self._srv.close()
            self._loop.run_until_complete(self._srv.wait_closed())
            self._loop.run_until_complete(self._app.shutdown())
            self._loop.run_until_complete(self._handler.shutdown(60.0))
            self._loop.run_until_complete(self._app.cleanup())

    async def _authorize(
            self, app: web.Application, handler: Handler) -> Handler:
        """ Middleware to check the authorization of the request. """
        async def middleware(request: web.Request) -> web.Response:
            """ Middleware handler to check authorization. """
            authorization = request.headers.get('Authorization')
            if authorization is None:
                return web.HTTPForbidden()
            split = authorization.split(' ')
            if len(split) != 2 or split[0] != 'Basic':
                return web.HTTPForbidden()
            credentials = split[1]
            credentials_decoded = base64.b64decode(credentials).decode('ASCII')
            username_password = credentials_decoded.split(':')
            if (len(username_password) != 2
                    or username_password[0] != self._username
                    or username_password[1] != self._password):
                return web.HTTPForbidden()
            return await handler(request)
        return middleware

    async def _rest(self, app: web.Application, handler: Handler) -> Handler:
        """ Middleware will convert data to/from python dictionary and call handler. """
        async def middleware(request: web.Request) -> web.Response:
            """ Middleware handler. """
            if request.method == "GET":
                request.data = request.query_string
            else:
                content_type = request.content_type
                if content_type == "application/json":
                    request.data = await request.json()
                else:
                    return web.HTTPNotAcceptable()

            for accept in request.headers.getall('ACCEPT', []):
                if accept == "application/json":
                    data_out = await handler(request)
                    return web.json_response(data_out)

            return web.HTTPNotAcceptable()
        return middleware
