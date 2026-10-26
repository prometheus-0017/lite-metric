"""
CPU 指标采集脚本
每秒采集一次 CPU 相关指标，通过 WebSocket RPC 批量上报到后端
依赖: pip install psutil xuri_rpc_websocket
"""

import time
import asyncio
import psutil
import signal
import sys

from xuri_rpc_websocket import createMain
from async_handler import AsyncMetricHandler
RPC_HOST = "localhost"
RPC_PORT = 13333
RPC_PATH = "/"


# ─── 指标构建 ─────────────────────────────────────────────────────────────────

def build_metrics_batch() -> list:
    """构建一轮采集的指标数据列表"""
    batch = []

    # 1. CPU 总使用率 (%)
    cpu_percent = psutil.cpu_percent(interval=None)
    batch.append({
        "id": "cpu_usage_percent",
        "name": "CPU 使用率",
        "value": cpu_percent,
        "data_type": "number",
        "save_mode": "series",
    })

    # 2. 各逻辑核心使用率 (%) - object_list 形式
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    cpu_cores = [
        {"key": f"core_{i}", "value": pct}
        for i, pct in enumerate(per_cpu)
    ]
    batch.append({
        "id": "cpu_per_core",
        "name": "各核心使用率",
        "value": cpu_cores,
        "data_type": "object_list",
        "save_mode": "latest",
    })

    # 2.1 每个核心独立 series 指标
    for i, pct in enumerate(per_cpu):
        batch.append({
            "id": f"cpu_core_{i}",
            "name": f"核心 {i} 使用率",
            "value": pct,
            "data_type": "number",
            "save_mode": "series",
        })

    # 3. CPU 频率 (MHz)
    try:
        freq = psutil.cpu_freq()
        if freq:
            batch.append({
                "id": "cpu_freq_current",
                "name": "CPU 当前频率",
                "value": freq.current,
                "data_type": "number",
                "save_mode": "latest",
            })
            batch.append({
                "id": "cpu_freq_max",
                "name": "CPU 最高频率",
                "value": freq.max,
                "data_type": "number",
                "save_mode": "max",
            })
            batch.append({
                "id": "cpu_freq_min",
                "name": "CPU 最低频率",
                "value": freq.min,
                "data_type": "number",
                "save_mode": "min",
            })
    except Exception:
        pass

    # 4. 系统 CPU 统计信息（对象列表）
    try:
        cpu_stats = psutil.cpu_stats()
        stats_list = [
            {"key": "ctx_switches", "value": cpu_stats.ctx_switches},
            {"key": "interrupts", "value": cpu_stats.interrupts},
            {"key": "soft_interrupts", "value": cpu_stats.soft_interrupts},
            {"key": "syscalls", "value": cpu_stats.syscalls},
        ]
        batch.append({
            "id": "cpu_stats",
            "name": "CPU 统计信息",
            "value": stats_list,
            "data_type": "object_list",
            "save_mode": "series",
        })
    except Exception:
        pass

    # 5. 系统平均负载（字符串形式）
    try:
        load1, load5, load15 = psutil.getloadavg()
        load_str = f"{load1:.2f} {load5:.2f} {load15:.2f}"
        batch.append({
            "id": "cpu_load_avg",
            "name": "系统负载",
            "value": load_str,
            "data_type": "string",
            "save_mode": "latest",
        })
    except Exception:
        # Windows 不支持 getloadavg
        pass

    return batch


# ─── RPC 上报 ─────────────────────────────────────────────────────────────────

async def rpc_send(metric_handler:AsyncMetricHandler, batch: list):
    """通过 RPC 调用后端 collect_metrics"""
    try:
        result = await metric_handler.collectMetrics(batch)
        return result
    except Exception as e:
        print(f"[ERROR] RPC 上报异常: {e}")
        return None


# ─── 主循环 ───────────────────────────────────────────────────────────────────

async def main():
    print("CPU 指标采集器启动（RPC 模式），每秒采集一次，Ctrl+C 停止...")

    # 预热 psutil
    psutil.cpu_percent(interval=None, percpu=True)
    await asyncio.sleep(0.5)

    # 建立 RPC 连接
    print(f"正在连接 {RPC_HOST}:{RPC_PORT}...")
    try:
        client, metric_handler = await createMain(
            "cpu_collector", RPC_HOST, RPC_PORT, RPC_PATH
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
            print('1')
            batch = build_metrics_batch()
            print('2')
            await rpc_send(metric_handler, batch)
            print('3')
        except Exception as e:
            print(f"[ERROR] 采集异常: {e}")
        await asyncio.sleep(1)

    print("采集器已停止。")


if __name__ == "__main__":
    from xuri_rpc import setDebugFlag
    setDebugFlag(True)
    asyncio.run(main())
