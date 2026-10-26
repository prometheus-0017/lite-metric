from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import asyncio
import threading
import json
import websockets
from models import Metric, init_db
import xuri_rpc_websocket
app = Flask(__name__)
CORS(app)

# 初始化数据库
init_db()

# 内存存储指标数据，以 id 为 key
metrics_store: dict[str, Metric] = {}

# ─── WebSocket 相关 ───────────────────────────────────────────────────────────
ws_clients: dict[websockets.WebSocketServerProtocol, set[str]] = {}  # ws -> set(metric_id)
_ws_loop: asyncio.AbstractEventLoop = None  # WebSocket 线程的事件循环引用

async def _ws_handler(ws):
    """处理单个 WebSocket 客户端连接"""
    ws_clients[ws] = set()
    try:
        async for message in ws:
            try:
                data = json.loads(message)
                action = data.get('action')

                if action == 'subscribe':
                    ids = data.get('ids', [])
                    ws_clients[ws].update(ids)
                    await ws.send(json.dumps({'type': 'subscribed', 'ids': list(ws_clients[ws])}))

                elif action == 'unsubscribe':
                    ids = data.get('ids', [])
                    ws_clients[ws] -= set(ids)
                    await ws.send(json.dumps({'type': 'unsubscribed', 'ids': list(ws_clients[ws])}))

            except json.JSONDecodeError:
                await ws.send(json.dumps({'error': 'Invalid JSON'}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        ws_clients.pop(ws, None)


async def _broadcast(metric_id: str, payload: dict):
    """将指标更新推送给所有订阅了该指标的客户端（必须在 WS 事件循环中执行）"""
    msg = json.dumps({'type': 'update', 'id': metric_id, 'data': payload})
    targets = [ws for ws, ids in ws_clients.items() if metric_id in ids]
    if targets:
        await asyncio.gather(
            *[ws.send(msg) for ws in targets],
            return_exceptions=True
        )


def broadcast(metric_id: str, payload: dict):
    """线程安全地从任意线程向 WebSocket 客户端广播（供 Flask 路由调用）"""
    if _ws_loop is not None:
        asyncio.run_coroutine_threadsafe(_broadcast(metric_id, payload), _ws_loop)


def _start_ws_server():
    """在新线程中启动 WebSocket 服务（端口 3003）"""
    global _ws_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _ws_loop = loop  # 保存引用，供主线程投递广播任务
    async def func():
        res=await xuri_rpc_websocket.createServer('host','0.0.0.0',13333)
        serve=res[0]
        from async_handler import AsyncMetricHandler
        await serve(AsyncMetricHandler(metrics_store, None))

    print('[WebSocket] Server started on ws://0.0.0.0:3003')
    loop.run_until_complete(func())
    loop.run_forever()
# ─── End WebSocket ─────────────────────────────────────────────────────────────


@app.route('/api/metrics', methods=['POST'])
def collect_metrics():
    """批量接收指标数据，接收一个列表"""
    try:
        data_list = request.get_json()

        if not isinstance(data_list, list):
            return jsonify({'error': 'Request body must be a JSON array'}), 400

        results = []
        for data in data_list:
            if not data or 'value' not in data:
                results.append({'error': 'Missing required field: value', 'data': data})
                continue

            # id 由后端自动生成（首次创建时），采集端可传可不传
            mid = data.get('id')
            value = data['value']
            name = data.get('name', '')
            data_type = data.get('data_type', 'number')
            save_mode = data.get('save_mode', 'latest')
            persist = data.get('persist', False)

            if mid:
                # 指定了 id，查找已有
                if mid in metrics_store:
                    existing = metrics_store[mid]
                    if existing.data_type != data_type or existing.save_mode != save_mode:
                        results.append({
                            'error': f'Metric "{mid}" already exists with different type/mode',
                            'id': mid
                        })
                        continue
                    existing.persist = persist
                    if name:
                        existing.name = name
                    existing.update(value)
                    broadcast(mid, existing.to_update_payload())
                    results.append({'status': 'success', 'id': mid})
                    continue

            # 创建新指标
            if not mid:
                mid = str(uuid.uuid4())
            metrics_store[mid] = Metric(id=mid, name=name, data_type=data_type, save_mode=save_mode, persist=persist)
            metrics_store[mid].update(value)
            broadcast(mid, metrics_store[mid].to_update_payload())
            results.append({'status': 'success', 'id': mid})

        return jsonify({'results': results}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics/query', methods=['POST'])
def query_metrics():
    """根据 id 列表查询指标数据"""
    try:
        data = request.get_json()

        if not data or 'ids' not in data or not isinstance(data['ids'], list):
            return jsonify({'error': 'Request body must contain an "ids" array'}), 400

        ids = data['ids']
        metrics_data = {}
        for mid in ids:
            if mid in metrics_store:
                metrics_data[mid] = metrics_store[mid].to_dict()

        return jsonify(metrics_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics/ids', methods=['GET'])
def get_metric_ids():
    """获取所有已注册的指标 id 列表（用于前端发现）"""
    return jsonify({'ids': list(metrics_store.keys())})


@app.route('/api/metrics/<mid>/persist', methods=['POST'])
def toggle_persist(mid):
    """切换指标的持久化标志"""
    if mid not in metrics_store:
        return jsonify({'error': 'Metric not found'}), 404

    data = request.get_json() or {}
    persist = data.get('persist', True)
    metrics_store[mid].persist = bool(persist)

    return jsonify({
        'status': 'success',
        'id': mid,
        'persist': metrics_store[mid].persist
    }), 200


@app.route('/api/metrics/<mid>', methods=['DELETE'])
def delete_metric(mid):
    """删除特定指标"""
    if mid in metrics_store:
        del metrics_store[mid]
        return jsonify({'status': 'success'}), 200
    return jsonify({'error': 'Metric not found'}), 404


if __name__ == '__main__':
    # 在新线程中启动 WebSocket 服务（端口 3003）
    ws_thread = threading.Thread(target=_start_ws_server, daemon=True)
    ws_thread.start()

    # 关闭 debug 避免 reloader 产生子进程导致 WebSocket 服务重复创建
    app.run(debug=False, host='0.0.0.0', port=12110)
