import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

DB_PATH = os.path.join(os.path.dirname(__file__), 'metrics.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS metric_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            collect_time REAL NOT NULL,
            data_content TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_metric_name ON metric_records(metric_name)
    ''')
    conn.commit()
    conn.close()


def persist_record(metric_name: str, value: Any):
    """将一条采集记录写入数据库"""
    conn = get_db()
    conn.execute(
        'INSERT INTO metric_records (metric_name, collect_time, data_content) VALUES (?, ?, ?)',
        (metric_name, datetime.now().timestamp(), json.dumps(value, ensure_ascii=False))
    )
    conn.commit()
    conn.close()


class Metric:
    """
    指标数据模型

    数据类型 (data_type):
      - string: 字符串
      - number: 数值
      - object_list: 对象列表，每个对象必须有 key 和 value 字段

    保存方式 (save_mode):
      - series: 序列，只存最近60条
      - max: 最大值，字符串行为为保留最新数值，对象列表行为为保留每个key在历史中的最大值
      - min: 最小值，字符串行为为保留最新数值，对象列表行为为保留每个key在历史中的最小值
      - latest: 最新值

    持久化 (persist):
      - 为 True 时，每次 update 都会将记录写入 SQLite 数据库
    """

    VALID_DATA_TYPES = ('string', 'number', 'object_list')
    VALID_SAVE_MODES = ('series', 'max', 'min', 'latest')
    MAX_SERIES_LEN = 60

    def __init__(self, id: str, name: str, data_type: str, save_mode: str, persist: bool = False):
        if data_type not in self.VALID_DATA_TYPES:
            raise ValueError(f"Invalid data_type: {data_type}")
        if save_mode not in self.VALID_SAVE_MODES:
            raise ValueError(f"Invalid save_mode: {save_mode}")

        self.id = id
        self.name = name  # 展示标签
        self.data_type = data_type
        self.save_mode = save_mode
        self.persist = persist

        # 当前展示值
        self.current_value: Optional[Union[str, float, List[Dict[str, Any]]]] = None
        # 最近一次更新的时间戳
        self.timestamp: Optional[float] = None
        # 序列数据（series模式使用）
        self.series: List[Dict[str, Any]] = []
        # 历史最大值（max模式使用）
        self.hist_max: Optional[Union[str, float, Dict[str, float]]] = None
        # 历史最小值（min模式使用）
        self.hist_min: Optional[Union[str, float, Dict[str, float]]] = None

    def update(self, value: Union[str, float, List[Dict[str, Any]]]):
        """更新指标数据"""
        self._validate_value(value)
        self.timestamp = datetime.now().timestamp()

        if self.save_mode == 'series':
            self.series.append({'timestamp': self.timestamp, 'value': value})
            if len(self.series) > self.MAX_SERIES_LEN:
                self.series.pop(0)
            self.current_value = value

        elif self.save_mode == 'latest':
            self.current_value = value

        elif self.save_mode == 'max':
            self.current_value = self._apply_max(value)

        elif self.save_mode == 'min':
            self.current_value = self._apply_min(value)

        # 持久化写入数据库
        if self.persist:
            persist_record(self.id, value)

    def _validate_value(self, value):
        """校验值类型是否匹配数据类型"""
        if self.data_type == 'string':
            if not isinstance(value, str):
                raise ValueError(f"Expected string, got {type(value).__name__}")
        elif self.data_type == 'number':
            if not isinstance(value, (int, float)):
                raise ValueError(f"Expected number, got {type(value).__name__}")
        elif self.data_type == 'object_list':
            if not isinstance(value, list):
                raise ValueError(f"Expected list, got {type(value).__name__}")
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError(f"Each item must be a dict")
                if 'key' not in item or 'value' not in item:
                    raise ValueError("Each object must have 'key' and 'value' fields")

    def _apply_max(self, value) -> Union[str, float, List[Dict[str, Any]]]:
        if self.data_type == 'string':
            return value
        elif self.data_type == 'number':
            if self.hist_max is None or value > self.hist_max:
                self.hist_max = value
            return self.hist_max
        elif self.data_type == 'object_list':
            if self.hist_max is None:
                self.hist_max = {item['key']: item['value'] for item in value}
            else:
                for item in value:
                    k, v = item['key'], item['value']
                    if k not in self.hist_max or (isinstance(v, (int, float)) and v > self.hist_max[k]):
                        self.hist_max[k] = v
            return [{'key': k, 'value': v} for k, v in self.hist_max.items()]

    def _apply_min(self, value) -> Union[str, float, List[Dict[str, Any]]]:
        if self.data_type == 'string':
            return value
        elif self.data_type == 'number':
            if self.hist_min is None or value < self.hist_min:
                self.hist_min = value
            return self.hist_min
        elif self.data_type == 'object_list':
            if self.hist_min is None:
                self.hist_min = {item['key']: item['value'] for item in value}
            else:
                for item in value:
                    k, v = item['key'], item['value']
                    if k not in self.hist_min or (isinstance(v, (int, float)) and v < self.hist_min[k]):
                        self.hist_min[k] = v
            return [{'key': k, 'value': v} for k, v in self.hist_min.items()]

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'name': self.name,
            'data_type': self.data_type,
            'save_mode': self.save_mode,
            'persist': self.persist,
            'timestamp': self.timestamp,
        }

        if self.save_mode == 'series':
            result['data'] = self.series
        else:
            result['value'] = self.current_value

        return result

    def to_update_payload(self) -> Dict[str, Any]:
        """WebSocket 广播用的精简载荷，只含 value + timestamp"""
        if self.save_mode == 'series':
            # series 模式推送最新一条数据
            latest = self.series[-1] if self.series else None
            return {'value': latest['value'] if latest else None, 'timestamp': self.timestamp}
        return {'value': self.current_value, 'timestamp': self.timestamp}
