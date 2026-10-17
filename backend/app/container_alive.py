"""ADR-1012 段階3 便D: コンテナの健康診断が読む「生きている印」。

docker-compose.yml の healthcheck が、印のファイルの更新時刻の古さで判定する。
印は /tmp（tmpfs）に置く。書けなくても本来の処理は止めない。
このファイルは celery を import しない（discord-gateway からも使うため）。
"""

import logging
import os

logger = logging.getLogger(__name__)

WORKER_ALIVE_PATH = "/tmp/celery-worker-alive"
BEAT_ALIVE_PATH = "/tmp/celery-beat-alive"
GATEWAY_ALIVE_PATH = "/tmp/discord-gateway-alive"
TOUCH_INTERVAL_SECONDS = 30.0


def touch_alive(path: str) -> None:
    """印のファイルを作るか、更新時刻を今にする。失敗しても例外を出さない。"""
    try:
        with open(path, "a"):
            pass
        os.utime(path, None)
    except OSError:
        logger.warning("生きている印の更新に失敗（処理は継続）: %s", path, exc_info=True)
