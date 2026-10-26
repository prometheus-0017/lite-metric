import { reactive } from 'vue'

/**
 * 指标注册中心
 * 组件通过 register(id) 注册自己需要的指标，
 * 通过 unregister(id) 注销。
 * registeredIds 是一个响应式集合，App.vue 监听它来查询指标。
 */

const registeredIds = reactive<Set<string>>(new Set())

export function register(id: string) {
  registeredIds.add(id)
}

export function unregister(id: string) {
  registeredIds.delete(id)
}

export function getRegisteredNames(): string[] {
  return Array.from(registeredIds)
}

export { registeredIds }
