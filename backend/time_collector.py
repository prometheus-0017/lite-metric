"""
时间采集脚本
每秒发送当前时间戳，通过 WebSocket RPC 上报到后端
"""

import time
import asyncio
import signal
from datetime import datetime

from xuri_rpc_websocket import createMain
from async_handler import AsyncMetricHandler

RPC_HOST = "localhost"
RPC_PORT = 13333
RPC_PATH = "/"


def build_time_metric() -> list:
    """构建当前时间戳指标"""
    now = time.time()
    print(f"[time_collector] {datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}")
    return [{
        "id": "time",
        "name": "当前时间",
        "value": now,
        "data_type": "number",
        "save_mode": "latest",
    }]


async def rpc_send(metric_handler: AsyncMetricHandler, batch: list):
    """通过 RPC 上报"""
    try:
        result = await metric_handler.collectMetrics(batch)
        return result
    except Exception as e:
        print(f"[ERROR] RPC 上报异常: {e}")
        return None


async def main():
    print("时间采集器启动，每秒上报一次当前时间，Ctrl+C 停止...")

    print(f"正在连接 {RPC_HOST}:{RPC_PORT}...")
    try:
        client, metric_handler = await createMain(
            "time_collector", RPC_HOST, RPC_PORT, RPC_PATH
        )
        print("RPC 连接成功。")
    except Exception as e:
        print(f"[ERROR] 无法连接后端: {e}")
        return

    running = True

    def handle_exit(sig, frame):
        nonlocal running
        print("\n收到退出信号，正在停止...")
        running = False

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    while running:
        try:
            batch = build_time_metric()
            await rpc_send(metric_handler, batch)
        except Exception as e:
            print(f"[ERROR] 采集异常: {e}")
        await asyncio.sleep(1)

    print("采集器已停止。")


if __name__ == "__main__":
    asyncio.run(main())
