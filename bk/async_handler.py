"""
异步 API 处理器
封装所有指标相关的业务逻辑，每个方法都是异步的
"""

import asyncio
import copy
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from models import Metric


class MetricSubscriber:
    """
    指标订阅器（对应一个远程方）
    一个订阅器可订阅多个指标，通过 addCallback 统一接收所有变更通知
    """

    def __init__(self, handler: 'AsyncMetricHandler'):
        self._handler = handler
        # 已订阅的指标 ID 集合
        self._subscribedIds: set = set()
        # 统一的回调列表，签名: (metricId, payload) -> None 或 async
        self._callback: Callable = []
        # metricId -> 上一次分发的值（用于 max/min/latest 变更检测）
        self._lastValues: Dict[str, Any] = {}
        # metricId -> 订阅时间戳（用于 series 模式过滤历史数据）
        self._subscribeTimestamps: Dict[str, float] = {}

    def register(self, metricId: str):
        """
        订阅指定指标

        Args:
            metricId: 指标 ID
        """
        self._subscribedIds.add(metricId)
        now = datetime.now().timestamp()
        # 记录订阅时间戳，后续只分发此时间点之后的数据
        self._subscribeTimestamps[metricId] = now
        # 如果指标已存在，立即用当前值初始化 _lastValues
        if metricId in self._handler.metrics_store:
            metric = self._handler.metrics_store[metricId]
            self._lastValues[metricId] = copy.deepcopy(metric.current_value)
            # print(f'[MetricSubscriber] register {metricId}, init lastValue={self._lastValues[metricId]}')
        else:
            # print(f'[MetricSubscriber] register {metricId}, metric not exist yet')
            pass

    def unregister(self, metricId: str):
        """
        取消订阅指定指标

        Args:
            metricId: 指标 ID
        """
        self._subscribedIds.discard(metricId)
        self._lastValues.pop(metricId, None)
        self._subscribeTimestamps.pop(metricId, None)

    # def addCallback(self, callback: Callable):
    #     """
    #     添加变更回调，所有已订阅指标的变更都会通过此回调通知

    #     Args:
    #         callback: 回调函数，签名: (metricId, payload) -> None 或 async (metricId, payload) -> None
    #     """
    #     self._callbacks.append(callback)
    #     print(f'[MetricSubscriber] addCallback: now {len(self._callbacks)} callback(s). callback={callback}')

    async def notify(self, metricId: str, metric: Metric):
        """
        由 AsyncMetricHandler 调用，分发数据变更给订阅者

        对于 max/min/latest 模式：仅当数值发生变更时回调
        对于其他模式（series）：始终回调当前数据

        Args:
            metricId: 指标 ID
            metric: 指标对象
        """
        if metricId not in self._subscribedIds:
            print(f'[MetricSubscriber] notify skip {metricId}, not subscribed. subscribed={self._subscribedIds}')
            return

        save_mode = metric.save_mode

        if save_mode in ('max', 'min', 'latest'):
            # 数值变更检测：展示值未变则不分发
            currentVal = metric.current_value
            lastVal = self._lastValues.get(metricId)
            if currentVal == lastVal:
                # print(f'[MetricSubscriber] notify skip {metricId}, no change. val={currentVal}')
                return
            # print(f'[MetricSubscriber] notify {metricId} changed: {lastVal} -> {currentVal}')
            self._lastValues[metricId] = copy.deepcopy(currentVal)
            payload = {'value': currentVal, 'timestamp': metric.timestamp}
        else:
            # series 等模式：只分发订阅时间之后的数据
            subTs = self._subscribeTimestamps.get(metricId, 0)
            filteredSeries = [item for item in metric.series if item['timestamp'] > subTs]
            if not filteredSeries:
                # print(f'[MetricSubscriber] notify skip {metricId} (series), no new data after subTs={subTs}, series_len={len(metric.series)}')
                return
            # print(f'[MetricSubscriber] notify {metricId} (series), {len(filteredSeries)} new points after subTs={subTs}')
            payload = {
                'value': filteredSeries[-1]['value'],
                'timestamp': metric.timestamp,
                'series': filteredSeries
            }

        # 分发给所有注册的回调
        # print(f'[MetricSubscriber] dispatching to {len(self._callbacks)} callback(s) for {metricId}')
        cb = self._callback
        try:
            # print(f'[MetricSubscriber] calling callback {cb} for {metricId}, payload_keys={list(payload.keys()) if isinstance(payload, dict) else "N/A"}')
            result = cb(metricId, payload)
            # 兼容同步回调和返回 coroutine 的远程代理回调
            if asyncio.iscoroutine(result):
                # print(f'[MetricSubscriber] awaiting callback coroutine for {metricId}')
                await result
                # print(f'[MetricSubscriber] callback completed for {metricId}')
        except Exception as e:
            import traceback
            # traceback.print_exc()
            # print(f'[MetricSubscriber] callback error for {metricId}: {e}')

    def getSubscribedIds(self) -> List[str]:
        """获取当前订阅的所有指标 ID"""
        return list(self._subscribedIds)


class AsyncMetricHandler:
    """异步指标处理对象"""

    def __init__(self, metrics_store: Dict[str, Metric], broadcast_fn=None):
        """
        初始化处理器

        Args:
            metrics_store: 指标存储字典
            broadcast_fn: 广播回调函数，签名: async (metric_id, payload) -> None
        """
        self.metrics_store = metrics_store
        self._broadcast_fn = broadcast_fn
        # 所有活跃的订阅器
        self._subscribers: List[MetricSubscriber] = []
        print(f'[AsyncMetricHandler] initialized, id={id(self)}')

    async def collectMetrics(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量接收指标数据

        Args:
            data_list: 指标数据列表

        Returns:
            包含 results 的字典
        """
        if not isinstance(data_list, list):
            return {'error': 'Request body must be a JSON array'}

        # print(f'[AsyncMetricHandler.collectMetrics] id={id(self)}, {len(data_list)} items, {len(self._subscribers)} subscriber(s)')

        results = []
        for data in data_list:
            if not data or 'value' not in data:
                results.append({'error': 'Missing required field: value', 'data': data})
                continue

            mid = data.get('id')
            value = data['value']
            name = data.get('name', '')
            data_type = data.get('data_type', 'number')
            save_mode = data.get('save_mode', 'latest')
            persist = data.get('persist', False)

            if mid:
                # 指定了 id，查找已有
                if mid in self.metrics_store:
                    existing = self.metrics_store[mid]
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
                    await self._broadcast(mid, existing.to_update_payload())
                    await self._dispatchToSubscribers(mid, existing)
                    results.append({'status': 'success', 'id': mid})
                    continue

            # 创建新指标
            if not mid:
                mid = str(uuid.uuid4())
            self.metrics_store[mid] = Metric(
                id=mid, name=name, data_type=data_type,
                save_mode=save_mode, persist=persist
            )
            self.metrics_store[mid].update(value)
            await self._broadcast(mid, self.metrics_store[mid].to_update_payload())
            await self._dispatchToSubscribers(mid, self.metrics_store[mid])
            results.append({'status': 'success', 'id': mid})

        return {'results': results}

    async def queryMetrics(self, ids: List[str]) -> Dict[str, Any]:
        """
        根据 id 列表查询指标数据

        Args:
            ids: 指标 ID 列表

        Returns:
            指标数据字典
        """
        if not ids or not isinstance(ids, list):
            return {'error': 'Request body must contain an "ids" array'}

        metrics_data = {}
        for mid in ids:
            if mid in self.metrics_store:
                metrics_data[mid] = self.metrics_store[mid].to_dict()

        return metrics_data

    async def getMetricIds(self) -> Dict[str, Any]:
        """
        获取所有已注册的指标 id 列表

        Returns:
            包含 ids 列表的字典
        """
        return {'ids': list(self.metrics_store.keys())}

    async def togglePersist(self, mid: str, persist: bool = True) -> Dict[str, Any]:
        """
        切换指标的持久化标志

        Args:
            mid: 指标 ID
            persist: 是否持久化

        Returns:
            操作结果
        """
        if mid not in self.metrics_store:
            return {'error': 'Metric not found'}

        self.metrics_store[mid].persist = bool(persist)

        return {
            'status': 'success',
            'id': mid,
            'persist': self.metrics_store[mid].persist
        }

    async def deleteMetric(self, mid: str) -> Dict[str, Any]:
        """
        删除特定指标

        Args:
            mid: 指标 ID

        Returns:
            操作结果
        """
        if mid in self.metrics_store:
            del self.metrics_store[mid]
            return {'status': 'success'}
        return {'error': 'Metric not found'}

    def createSubscriber(self,callback) -> MetricSubscriber:
        """
        创建一个指标订阅器

        Returns:
            MetricSubscriber 实例
        """
        subscriber = MetricSubscriber(self)
        subscriber._callback=callback
        self._subscribers.append(subscriber)
        print(f'[AsyncMetricHandler.createSubscriber] id={id(self)}, created subscriber #{len(self._subscribers)}, subscribers={self._subscribers}')
        return subscriber

    def removeSubscriber(self, subscriber: MetricSubscriber):
        """
        移除订阅器

        Args:
            subscriber: 要移除的订阅器
        """
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    async def _dispatchToSubscribers(self, metricId: str, metric: Metric):
        """将数据变更分发给所有订阅了该指标的订阅器"""
        print(f'[AsyncMetricHandler._dispatchToSubscribers] id={id(self)}, metricId={metricId}, {len(self._subscribers)} subscriber(s)')
        for i, subscriber in enumerate(self._subscribers):
            # print(f'  -> subscriber[{i}]: subscribedIds={subscriber.getSubscribedIds()}, callbacks={len(subscriber._callback)}')
            await subscriber.notify(metricId, metric)

    async def _broadcast(self, metric_id: str, payload: Dict[str, Any]):
        """内部广播方法，调用外部注入的广播函数"""
        if self._broadcast_fn:
            await self._broadcast_fn(metric_id, payload)
