"""本地开发用的 Redis 兼容服务（fakeredis TCP Server）。

无真实 Redis 环境时替代 broker / 缓存 / 限流 / JWT 黑名单，
监听 127.0.0.1:6379，默认 16 个 db（与 .env 的 db0/1/2 兼容）。

用法: python scripts/fake_redis_server.py
"""

from __future__ import annotations

import logging

from fakeredis import TcpFakeServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_logger = logging.getLogger("fake_redis_server")

HOST = "127.0.0.1"
PORT = 6379
DBS = 16


def main() -> None:
    server = TcpFakeServer((HOST, PORT), server_type="redis")
    _logger.info("fake redis serving on %s:%s with %d db", HOST, PORT, DBS)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _logger.info("fake redis stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
