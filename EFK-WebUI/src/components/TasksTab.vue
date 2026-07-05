<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import draggable from 'vuedraggable'
import NestedDraggable from './NestedDraggable.vue'

const props = defineProps({
  apiCall: {
    type: Function,
    required: true
  }
})

const flows = ref([])
const editingFlow = ref(null)
const activeStepId = ref(null)
const autographLibs = ref([])
const autographLibFiles = ref({})

const loadFlows = async () => {
  const result = await props.apiCall('get_flows')
  if (result) {
    flows.value = result
  }
  const libsResult = await props.apiCall('get_autograph_libs')
  if (libsResult) {
    autographLibs.value = libsResult
    if (editingFlow.value) {
      for (const lib of libsResult) {
        const files = await props.apiCall('get_autograph_lib_files', lib)
        autographLibFiles.value[lib] = files || []
      }
    }
  }
}

let pollInterval = null
onMounted(() => {
  loadFlows()
  pollInterval = setInterval(loadFlows, 1000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const createNewFlow = () => {
  editingFlow.value = {
    id: `flow_${Date.now()}`,
    name: '新建自动化任务',
    enabled: false,
    steps: []
  }
  activeStepId.value = null
}

const editFlow = (flow) => {
  const f = JSON.parse(JSON.stringify(flow))
  const addIds = (arr) => {
    if (!arr) return
    arr.forEach(s => {
      if (!s._id) s._id = Date.now() + Math.random().toString()
      if (s.action === 'image_search' && !s.selected_files) s.selected_files = []
      if (s.condition_action) {
        s.condition_list = [s.condition_action]
        delete s.condition_action
      }
      if (!s.condition_list) s.condition_list = []
      if (!s.then) s.then = []
      if (!s.children) s.children = []
      addIds(s.condition_list)
      addIds(s.then)
      addIds(s.children)
    })
  }
  if (!f.steps) f.steps = []
  addIds(f.steps)
  editingFlow.value = f
  activeStepId.value = null
}

const saveFlow = async () => {
  const f = JSON.parse(JSON.stringify(editingFlow.value))
  const cleanStep = (s) => {
    delete s._id
    if (s.condition_list && s.condition_list.length > 0) {
      s.condition_action = cleanStep(s.condition_list[0])
    }
    delete s.condition_list
    if (s.then) s.then.forEach(cleanStep)
    if (s.children) s.children.forEach(cleanStep)
    if (s.action !== 'condition') delete s.then
    if (s.action !== 'loop') delete s.children
    return s
  }
  if (f.steps) f.steps.forEach(cleanStep)
  await props.apiCall('save_flow', f)
  editingFlow.value = null
  activeStepId.value = null
  loadFlows()
}

const deleteFlow = async (id) => {
  await props.apiCall('delete_flow', id)
  loadFlows()
}

const toggleFlow = async (flow) => {
  if (flow.enabled) {
    await props.apiCall('stop_flow', flow.id)
  } else {
    await props.apiCall('start_flow', flow.id)
  }
  loadFlows()
}

const removeStep = (id) => {
  if (activeStepId.value === id) activeStepId.value = null
  const findAndRemove = (arr) => {
    const idx = arr.findIndex(s => s._id === id)
    if (idx !== -1) {
      arr.splice(idx, 1)
      return true
    }
    for (const s of arr) {
      if (s.then && findAndRemove(s.then)) return true
      if (s.children && findAndRemove(s.children)) return true
      if (s.condition_list && findAndRemove(s.condition_list)) return true
    }
    return false
  }
  if (editingFlow.value && editingFlow.value.steps) {
    findAndRemove(editingFlow.value.steps)
  }
}

const activeStepData = computed(() => {
  if (!activeStepId.value || !editingFlow.value) return null
  let found = null
  const findStep = (arr) => {
    for (const s of arr) {
      if (s._id === activeStepId.value) { found = s; return }
      if (s.then) findStep(s.then)
      if (s.children) findStep(s.children)
      if (s.condition_list) findStep(s.condition_list)
      if (found) return
    }
  }
  findStep(editingFlow.value.steps)
  return found
})

const availableComponents = ref([
  { action: 'sleep', name: '延时' },
  { action: 'mouse_move', name: '鼠标移动' },
  { action: 'mouse_click', name: '鼠标点击' },
  { action: 'key_press', name: '键盘按键' },
  { action: 'image_search', name: '识图' },
  { action: 'condition', name: '条件(If)' },
  { action: 'loop', name: '循环(Loop)' },
  { action: 'call_flow', name: '调用任务' }
])

const cloneComponent = (cmp) => {
  let step = { action: cmp.action, _id: Date.now() + Math.random().toString() }
  if (cmp.action === 'sleep') step.duration = 1000
  if (cmp.action === 'mouse_move') { step.x = 0; step.y = 0; }
  if (cmp.action === 'mouse_click') { step.button = 'left'; step.modifier = 'none'; }
  if (cmp.action === 'key_press') { step.key = 'esc'; }
  if (cmp.action === 'image_search') { step.search_type = 'single'; step.target = ''; step.confidence = 0.8; step.click_after_search = 'none'; step.selected_files = []; }
  if (cmp.action === 'condition') { step.if = 'last_search_success'; step.then = []; step.condition_list = []; }
  if (cmp.action === 'loop') { step.count = -1; step.break_on_success = true; step.children = []; step.condition_list = []; }
  if (cmp.action === 'call_flow') { step.flow_id = ''; }
  return step
}

const getStepName = (action) => {
  const cmp = availableComponents.value.find(c => c.action === action)
  return cmp ? cmp.name : action
}
</script>

<template>
  <div>
    <!-- 列表视图 -->
    <div v-if="!editingFlow">
      <div class="flex" style="justify-content: flex-end; align-items: center; margin-bottom: 12px;">
        <button class="button-primary" style="padding: 6px 16px; font-size: 13px;" @click="createNewFlow">+ 新建任务</button>
      </div>

      <div class="grid-1col gap-md">
        <section v-for="flow in flows" :key="flow.id" class="store-utility-card flex" style="justify-content: space-between; align-items: center;">
          <div>
            <h3 class="body-strong">{{ flow.name }}</h3>
            <div class="caption muted mt-xs">{{ flow.steps ? flow.steps.length : 0 }} 个步骤</div>
          </div>
          <div class="flex gap-sm align-center">
            <button class="button-dark-utility" @click="editFlow(flow)">编辑</button>
            <button class="button-dark-utility" style="background-color: #ff3b30;" @click="deleteFlow(flow.id)">删除</button>
            <button :class="flow.enabled ? 'button-primary' : 'button-pearl-capsule'" style="width: 80px;" @click="toggleFlow(flow)">
              {{ flow.enabled ? '运行中' : '已停止' }}
            </button>
          </div>
        </section>
        
        <div v-if="flows.length === 0" class="text-center caption muted mt-xl">
          暂无自动化任务，点击上方按钮新建。
        </div>
      </div>
    </div>

    <!-- 编辑视图 -->
    <div v-else>
      <div class="flex" style="justify-content: flex-end; align-items: center; margin-bottom: 12px;">
        <div class="flex gap-sm">
          <button class="button-pearl-capsule" style="padding: 6px 16px; font-size: 13px;" @click="editingFlow = null">取消</button>
          <button class="button-primary" style="padding: 6px 16px; font-size: 13px;" @click="saveFlow">保存</button>
        </div>
      </div>

      <section class="store-utility-card mb-md">
        <div class="form-row">
          <label class="body-strong">任务名称</label>
          <input type="text" v-model="editingFlow.name" class="search-input w-full mt-xs">
        </div>
      </section>

      <!-- 上方：嵌套式横向流程画布 -->
      <section class="store-utility-card mb-md">
        <h3 class="body-strong mb-md">流程画布 <span class="caption muted font-normal ml-sm">(点击任意方块编辑参数)</span></h3>
        
        <div style="background: var(--canvas-parchment); border-radius: 12px; border: 2px dashed var(--hairline); padding: 20px; overflow-x: auto;">
          <NestedDraggable
            :steps="editingFlow.steps"
            :activeStepId="activeStepId"
            :getStepName="getStepName"
            @select-step="id => activeStepId = id"
            @remove-step="removeStep"
          />
        </div>
      </section>

      <!-- 下方：可用组件库 -->
      <section class="store-utility-card">
        <h3 class="body-strong mb-md">组件库 <span class="caption muted font-normal ml-sm">(按住拖入上方)</span></h3>
        <draggable
          :list="availableComponents"
          :group="{ name: 'flow', pull: 'clone', put: false }"
          :clone="cloneComponent"
          item-key="action"
          :sort="false"
          class="flex gap-sm"
          style="flex-wrap: wrap;"
        >
          <template #item="{ element }">
            <div class="button-pearl-capsule cursor-move" style="user-select: none; border: 1px solid var(--primary); background: var(--canvas);">
              + {{ element.name }}
            </div>
          </template>
        </draggable>
      </section>
    </div>

    <!-- 浮层弹窗：编辑参数 -->
    <Teleport to="body">
      <div v-if="activeStepData" class="modal-overlay" @click.self="activeStepId = null">
        <div class="modal-content">
          <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 class="body-strong">配置: {{ getStepName(activeStepData.action) }}</h3>
            <button class="button-pearl-capsule" style="padding: 4px 10px; border-radius: 99px;" @click="activeStepId = null">完成</button>
          </div>
          
          <div class="params-form">
            <!-- 延时 -->
            <div v-if="activeStepData.action === 'sleep'" class="flex gap-sm align-center">
              <span class="caption">延时(毫秒):</span>
              <input type="number" v-model="activeStepData.duration" class="search-input" style="height: 32px; width: 120px;">
            </div>

            <!-- 鼠标移动 -->
            <div v-if="activeStepData.action === 'mouse_move'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">X 坐标:</span>
                <input type="number" v-model="activeStepData.x" class="search-input w-full" style="height: 32px;">
              </div>
              <div class="flex gap-sm align-center">
                <span class="caption">Y 坐标:</span>
                <input type="number" v-model="activeStepData.y" class="search-input w-full" style="height: 32px;">
              </div>
            </div>

            <!-- 鼠标点击 -->
            <div v-if="activeStepData.action === 'mouse_click'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">按键:</span>
                <select v-model="activeStepData.button" class="search-input w-full" style="height: 32px;">
                  <option value="left">左键</option>
                  <option value="right">右键</option>
                </select>
              </div>
              <div class="flex gap-sm align-center">
                <span class="caption">修饰键:</span>
                <select v-model="activeStepData.modifier" class="search-input w-full" style="height: 32px;">
                  <option value="none">无</option>
                  <option value="ctrl">Ctrl</option>
                  <option value="shift">Shift</option>
                </select>
              </div>
            </div>

            <!-- 键盘按键 -->
            <div v-if="activeStepData.action === 'key_press'" class="flex gap-sm align-center">
              <span class="caption">按键名:</span>
              <input type="text" v-model="activeStepData.key" class="search-input" style="height: 32px; width: 120px;" placeholder="如 esc, enter">
            </div>

            <!-- 识图 -->
            <div v-if="activeStepData.action === 'image_search'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">模式:</span>
                <select v-model="activeStepData.search_type" class="search-input flex-1" style="height: 32px;">
                  <option value="single">单张图片</option>
                  <option value="lib">自动化图库 (OR)</option>
                </select>
              </div>
              
              <div v-if="activeStepData.search_type === 'lib'">
                <div class="caption mb-xs">选择图库:</div>
                <select v-model="activeStepData.target" class="search-input w-full" style="height: 32px;" @change="activeStepData.selected_files = []">
                  <option disabled value="">请选择图库</option>
                  <option v-for="lib in autographLibs" :key="lib" :value="lib">{{ lib }}</option>
                </select>
                
                <div v-if="activeStepData.target" class="mt-xs">
                  <div class="caption mb-xs">选择指定图片 (不选则默认全库):</div>
                  <div style="max-height: 100px; overflow-y: auto; background: var(--canvas); border: 1px solid var(--hairline); border-radius: 6px; padding: 4px;">
                    <label v-for="file in autographLibFiles[activeStepData.target]" :key="file" class="flex gap-xs align-center" style="font-size: 12px; cursor: pointer; padding: 2px 4px;">
                      <input type="checkbox" :value="file" v-model="activeStepData.selected_files">
                      {{ file }}
                    </label>
                    <div v-if="!autographLibFiles[activeStepData.target]?.length" class="caption muted text-center py-xs">
                      该图库为空
                    </div>
                  </div>
                </div>
              </div>
              <div v-else>
                <div class="caption mb-xs">图片路径:</div>
                <input type="text" v-model="activeStepData.target" class="search-input w-full" style="height: 32px;">
              </div>

              <div class="flex gap-sm align-center mt-xs">
                <span class="caption">相似度(0-1):</span>
                <input type="number" step="0.1" v-model="activeStepData.confidence" class="search-input" style="height: 32px; width: 80px;">
              </div>
              <div class="flex gap-sm align-center mt-xs">
                <span class="caption">匹配后点击:</span>
                <select v-model="activeStepData.click_after_search" class="search-input flex-1" style="height: 32px;">
                  <option value="none">无动作</option>
                  <option value="left">移动至中心并左键点击</option>
                  <option value="right">移动至中心并右键点击</option>
                </select>
              </div>
            </div>

            <!-- 循环 -->
            <div v-if="activeStepData.action === 'loop'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">循环次数:</span>
                <input type="number" v-model="activeStepData.count" class="search-input" style="height: 32px; width: 120px;">
                <span class="caption muted">(-1为无限)</span>
              </div>
              <div class="flex gap-sm align-center mt-xs">
                <span class="caption">条件插槽触发时:</span>
                <select v-model="activeStepData.break_on_success" class="search-input flex-1" style="height: 32px;">
                  <option :value="true">退出循环 (Break)</option>
                  <option :value="false">继续循环</option>
                </select>
              </div>
            </div>
            
            <!-- 条件 -->
            <div v-if="activeStepData.action === 'condition'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">判定依据:</span>
                <select v-model="activeStepData.if" class="search-input w-full" style="height: 32px;">
                  <option value="last_search_success">上一次识图成功 (推荐通过条件插槽)</option>
                </select>
              </div>
            </div>
            
            <!-- 调用任务 -->
            <div v-if="activeStepData.action === 'call_flow'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">选择任务:</span>
                <select v-model="activeStepData.flow_id" class="search-input w-full" style="height: 32px;">
                  <option disabled value="">请选择要调用的任务</option>
                  <option v-for="f in flows.filter(f => f.id !== editingFlow.id)" :key="f.id" :value="f.id">{{ f.name }}</option>
                </select>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.cursor-move {
  cursor: grab;
}
.cursor-move:active {
  cursor: grabbing;
}

/* 横向流程图样式 */
.horizontal-flow {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  min-height: 80px;
}
.flow-step-item {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.flow-step-item::after {
  content: '→';
  margin: 0 16px;
  color: var(--ink-muted-48);
  font-weight: 600;
  font-size: 20px;
}
.horizontal-flow > *:last-child::after {
  display: none;
}

.flow-step-box {
  position: relative;
  width: 80px;
  height: 80px;
  background: var(--canvas);
  border: 2px solid var(--hairline);
  border-radius: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}
.flow-step-box:hover {
  border-color: var(--primary);
  transform: translateY(-2px);
}
.flow-step-box.active {
  border-color: var(--primary);
  background: rgba(0, 102, 204, 0.05);
}

.step-delete {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  background: #ff3b30;
  color: white;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 10;
}
.flow-step-box:hover .step-delete {
  opacity: 1;
}
.step-delete:hover {
  transform: scale(1.1);
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.4);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: var(--surface-pearl);
  padding: 24px;
  border-radius: 16px;
  width: 320px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.2);
  border: 1px solid var(--hairline);
}
</style>
