import asyncio
import inspect
import signal
from signal import (
    SIGABRT,
    SIGINT,
    SIGTERM,
    signal as signal_func,
)
from ssl import SSLZeroReturnError
from typing import (
    Any,
    Callable,
    List,
    Optional,
    TYPE_CHECKING,
)

import pytz
import uvicorn
from fastapi import FastAPI
from telegram.error import (
    NetworkError,
    TelegramError,
    TimedOut,
)
from telegram.ext import (
    AIORateLimiter,
    Application as TgApplication,
    Defaults,
)

from core.config import config as bot_config
from utils.log import logger
from utils.models.signal import Singleton

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from uvicorn import Server


class _Bot(Singleton):
    _tg_app: Optional[TgApplication] = None
    _web_app: Optional[FastAPI] = None
    _web_server: "Server" = None
    _web_server_task: Optional[asyncio.Task] = None

    _post_init_funcs: List[Callable[[TgApplication], Any]] = []
    _post_shutdown_funcs: List[Callable[[TgApplication], Any]] = []

    _running: False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def tg_app(self) -> TgApplication:
        """telegram app"""

        with self._lock:
            if self._tg_app is None:
                from telegram.request import HTTPXRequest

                self._tg_app = (
                    TgApplication.builder()
                    .rate_limiter(AIORateLimiter())
                    .defaults(Defaults(tzinfo=pytz.timezone("Asia/Shanghai")))
                    .token(bot_config.bot_token)
                    .request(
                        HTTPXRequest(
                            256,
                            proxy_url=bot_config.proxy_url,
                            read_timeout=bot_config.read_timeout,
                            write_timeout=bot_config.write_timeout,
                            connect_timeout=bot_config.connect_timeout,
                            pool_timeout=bot_config.pool_timeout,
                        )
                    )
                    .build()
                )
        return self._tg_app

    @property
    def web_app(self) -> FastAPI:
        """fastapi app"""
        with self._lock:
            if self._web_app is None:
                self._web_app = FastAPI(debug=bot_config.debug)
        return self._web_app

    @property
    def web_server(self) -> "Server":
        """uvicorn server"""
        with self._lock:
            if self._web_server is None:
                from uvicorn import Server

                self._web_server = Server(
                    uvicorn.Config(
                        app=self.web_app,
                        port=bot_config.webserver.port,
                        host=bot_config.webserver.host,
                        log_config=None,
                    )
                )
        return self._web_server

    def __init__(self) -> None:
        self._running = False

    async def _on_startup(self) -> None:
        for post_init in self._post_init_funcs:
            # todo: 参数解析
            if inspect.iscoroutinefunction(post_init):
                await post_init(self.tg_app)
            else:
                post_init(self.tg_app)

    async def _on_shutdown(self) -> None:
        for post_shutdown in self._post_shutdown_funcs:
            # todo: 参数解析
            if inspect.iscoroutinefunction(post_shutdown):
                await post_shutdown(self.tg_app)
            else:
                post_shutdown(self.tg_app)

    async def initialize(self):
        """BOT 初始化"""

    async def shutdown(self):
        """BOT 关闭"""

    async def start(self) -> None:
        """启动 BOT"""
        logger.info("正在启动 BOT 中...")

        def error_callback(exc: TelegramError) -> None:
            self.tg_app.create_task(self.tg_app.process_error(error=exc, update=None))

        await self.initialize()
        logger.success("BOT 初始化成功")

        await self.tg_app.initialize()

        server_config = self.web_server.config
        server_config.setup_event_loop()
        if not server_config.loaded:
            server_config.load()
        self.web_server.lifespan = server_config.lifespan_class(server_config)
        await self.web_server.startup()
        if self.web_server.should_exit:
            logger.error("web server 启动失败，正在退出")
            raise SystemExit

        self._web_server_task = asyncio.create_task(self.web_server.main_loop())

        for _ in range(5):  # 连接至 telegram 服务器
            try:
                await self.tg_app.updater.start_polling(error_callback=error_callback)
                break
            except TimedOut:
                logger.warning("连接至 [blue]telegram[/] 服务器失败，正在重试", extra={"markup": True})
                continue
            except NetworkError as e:
                logger.exception()
                if isinstance(e, SSLZeroReturnError):
                    logger.error("代理服务出现异常, 请检查您的代理服务是否配置成功.")
                else:
                    logger.error("网络连接出现问题, 请检查您的网络状况.")
                raise SystemExit
        await self._on_startup()
        await self.tg_app.start()
        self._running = True
        logger.success("BOT 启动成功")

    async def idle(self) -> None:
        """在接收到中止信号之前，堵塞loop"""

        signals = {k: v for v, k in signal.__dict__.items() if v.startswith("SIG") and not v.startswith("SIG_")}
        task = None

        def signal_handler(signum, _) -> None:
            logger.debug(f"接收到了终止信号 {signals[signum]} 正在退出...")
            task.cancel()
            self._web_server_task.cancel()

        for s in (SIGINT, SIGTERM, SIGABRT):
            signal_func(s, signal_handler)

        while True:
            task = asyncio.create_task(asyncio.sleep(600))

            try:
                await task
            except asyncio.CancelledError:
                break

    async def stop(self):
        """关闭"""
        logger.info("正在关闭 BOT")

        if self.tg_app.updater.running:
            await self.tg_app.updater.stop()
        if self.tg_app.running:
            await self.tg_app.stop()

        await self.tg_app.shutdown()
        if self._web_server is not None:
            await self._web_server.shutdown()

        await self._on_shutdown()
        await self.shutdown()
        logger.success("BOT 关闭成功")
        self._running = False

    def launch(self):
        """启动"""
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.start())
            loop.run_until_complete(self.idle())
        except (SystemExit, KeyboardInterrupt):
            pass
        finally:
            loop.run_until_complete(self.stop())

    # decorators

    def on_startup(self):
        """注册一个在 BOT 启动时执行的函数"""

    def on_shutdown(self):
        """注册一个在 BOT 停止时执行的函数"""


bot = _Bot()
