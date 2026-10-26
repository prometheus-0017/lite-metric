/** 数据类型枚举 */
export enum DataType {
  String = 'string',
  Number = 'number',
  ObjectList = 'object_list',
}

/** 保存方式枚举 */
export enum SaveMode {
  Latest = 'latest',
  Series = 'series',
  Max = 'max',
  Min = 'min',
}

/** 对象列表中的单个对象 */
export interface ObjectItem {
  key: string
  name: string
  value: number | string
}

/** 序列中的数据点 */
export interface DataPoint {
  timestamp: number
  value: number | string | ObjectItem[]
}

/** 指标数据项（后端返回） */
export interface MetricItem {
  id: string
  name: string
  data_type: DataType
  save_mode: SaveMode
  persist: boolean
  value?: number | string | ObjectItem[] | null
  data?: DataPoint[]
  timestamp?: number
}

// ─── AsyncMetricHandler 接口类型 ─────────────────────────────────────────────

/** 指标采集请求数据 */
export interface MetricCollectData {
  id?: string
  value: number | string | ObjectItem[]
  name?: string
  data_type?: DataType
  save_mode?: SaveMode
  persist?: boolean
}

/** 单个采集结果 */
export interface CollectResult {
  status?: 'success'
  id?: string
  error?: string
  data?: MetricCollectData
}

/** 批量采集响应 */
export interface CollectResponse {
  results: CollectResult[]
  error?: string
}

/** 查询响应 */
export interface QueryResponse {
  [id: string]: MetricItem
}

/** 获取所有 ID 响应 */
export interface MetricIdsResponse {
  ids: string[]
}

/** 切换持久化响应 */
export interface TogglePersistResponse {
  status: 'success' | 'error'
  id?: string
  persist?: boolean
  error?: string
}

/** 删除指标响应 */
export interface DeleteMetricResponse {
  status: 'success' | 'error'
  error?: string
}

/** 广播回调函数类型 */
export type BroadcastFn = (metricId: string, payload: MetricUpdatePayload) => Promise<void>

/** WebSocket 广播 / 订阅器回调载荷 */
export interface MetricUpdatePayload {
  value: number | string | ObjectItem[] | null
  timestamp: number
  /** series 模式下携带订阅时间窗口内的数据点 */
  series?: DataPoint[]
}

// ─── MetricSubscriber 类型 ─────────────────────────────────────────────────────

/** 指标订阅器（对应一个远程方） */
export interface IMetricSubscriber {
  register(metricId: string): Promise<void>
  unregister(metricId: string): Promise<void>
  getSubscribedIds(): Promise<string[]>
}

/** AsyncMetricHandler 接口定义 */
export interface IMetricHandler {
  collectMetrics(dataList: MetricCollectData[]): Promise<CollectResponse>
  queryMetrics(ids: string[]): Promise<QueryResponse>
  getMetricIds(): Promise<MetricIdsResponse>
  togglePersist(mid: string, persist?: boolean): Promise<TogglePersistResponse>
  deleteMetric(mid: string): Promise<DeleteMetricResponse>
  createSubscriber(callback:(metricId: string, payload: MetricUpdatePayload)=>Promise<void>): Promise<IMetricSubscriber>
}
