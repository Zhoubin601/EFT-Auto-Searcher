<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import draggable from 'vuedraggable'

const props = defineProps({
  apiCall: {
    type: Function,
    required: true
  }
})

const flows = ref([])
const editingFlow = ref(null)
const activeStepIndex = ref(null)

const loadFlows = async () => {
  const result = await props.apiCall('get_flows')
  if (result) {
    flows.value = result
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
  activeStepIndex.value = null
}

const editFlow = (flow) => {
  const f = JSON.parse(JSON.stringify(flow))
  if (f.steps) {
    f.steps.forEach(s => {
      if (!s._id) s._id = Date.now() + Math.random()
    })
  } else {
    f.steps = []
  }
  editingFlow.value = f
  activeStepIndex.value = null
}

const saveFlow = async () => {
  const f = JSON.parse(JSON.stringify(editingFlow.value))
  f.steps.forEach(s => {
    delete s._id
  })
  await props.apiCall('save_flow', f)
  editingFlow.value = null
  activeStepIndex.value = null
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

const removeStep = (index) => {
  if (activeStepIndex.value === index) {
    activeStepIndex.value = null
  } else if (activeStepIndex.value !== null && activeStepIndex.value > index) {
    activeStepIndex.value -= 1
  }
  editingFlow.value.steps.splice(index, 1)
}

const availableComponents = ref([
  { action: 'sleep', name: '延时' },
  { action: 'mouse_move', name: '鼠标移动' },
  { action: 'mouse_click', name: '鼠标点击' },
  { action: 'key_press', name: '键盘按键' },
  { action: 'image_search', name: '识图' }
])

const cloneComponent = (cmp) => {
  let step = { action: cmp.action, _id: Date.now() + Math.random() }
  if (cmp.action === 'sleep') step.duration = 1000
  if (cmp.action === 'mouse_move') { step.x = 0; step.y = 0; }
  if (cmp.action === 'mouse_click') { step.button = 'left'; step.modifier = 'none'; }
  if (cmp.action === 'key_press') { step.key = 'esc'; }
  if (cmp.action === 'image_search') { step.target = ''; step.confidence = 0.8; }
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
      <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <h2 class="display-md">自动化任务</h2>
        <button class="button-primary" @click="createNewFlow">新建任务</button>
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
      <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <h2 class="display-md">编辑任务</h2>
        <div class="flex gap-sm">
          <button class="button-pearl-capsule" @click="editingFlow = null">取消</button>
          <button class="button-primary" @click="saveFlow">保存</button>
        </div>
      </div>

      <section class="store-utility-card mb-md">
        <div class="form-row">
          <label class="body-strong">任务名称</label>
          <input type="text" v-model="editingFlow.name" class="search-input w-full mt-xs">
        </div>
      </section>

      <!-- 上方：横向流程画布 -->
      <section class="store-utility-card mb-md">
        <h3 class="body-strong mb-md">流程画布 <span class="caption muted font-normal ml-sm">(点击小方块编辑参数)</span></h3>
        
        <div style="background: var(--canvas-parchment); border-radius: 12px; border: 2px dashed var(--hairline); padding: 20px; overflow-x: auto;">
          <draggable
            v-model="editingFlow.steps"
            group="flow"
            item-key="_id"
            animation="200"
            class="horizontal-flow"
          >
            <template #item="{ element: step, index }">
              <div class="flow-step-item">
                <div class="flow-step-box" :class="{ 'active': activeStepIndex === index }" @click="activeStepIndex = index">
                  <div class="step-delete" @click.stop="removeStep(index)">×</div>
                  <div class="caption-strong text-primary">{{ getStepName(step.action) }}</div>
                </div>
              </div>
            </template>
            <!-- 空状态占位 -->
            <template #header v-if="editingFlow.steps.length === 0">
              <div class="text-center caption muted" style="line-height: 80px; width: 100%;">
                拖拽下方组件到这里
              </div>
            </template>
          </draggable>
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
      <div v-if="activeStepIndex !== null && editingFlow && editingFlow.steps[activeStepIndex]" class="modal-overlay" @click.self="activeStepIndex = null">
        <div class="modal-content">
          <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3 class="body-strong">配置: {{ getStepName(editingFlow.steps[activeStepIndex].action) }}</h3>
            <button class="button-pearl-capsule" style="padding: 4px 10px; border-radius: 99px;" @click="activeStepIndex = null">完成</button>
          </div>
          
          <div class="params-form">
            <!-- 延时 -->
            <div v-if="editingFlow.steps[activeStepIndex].action === 'sleep'" class="flex gap-sm align-center">
              <span class="caption">延时(毫秒):</span>
              <input type="number" v-model="editingFlow.steps[activeStepIndex].duration" class="search-input" style="height: 32px; width: 120px;">
            </div>

            <!-- 鼠标移动 -->
            <div v-if="editingFlow.steps[activeStepIndex].action === 'mouse_move'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">X 坐标:</span>
                <input type="number" v-model="editingFlow.steps[activeStepIndex].x" class="search-input w-full" style="height: 32px;">
              </div>
              <div class="flex gap-sm align-center">
                <span class="caption">Y 坐标:</span>
                <input type="number" v-model="editingFlow.steps[activeStepIndex].y" class="search-input w-full" style="height: 32px;">
              </div>
            </div>

            <!-- 鼠标点击 -->
            <div v-if="editingFlow.steps[activeStepIndex].action === 'mouse_click'" class="grid-1col gap-sm">
              <div class="flex gap-sm align-center">
                <span class="caption">按键:</span>
                <select v-model="editingFlow.steps[activeStepIndex].button" class="search-input w-full" style="height: 32px;">
                  <option value="left">左键</option>
                  <option value="right">右键</option>
                </select>
              </div>
              <div class="flex gap-sm align-center">
                <span class="caption">修饰键:</span>
                <select v-model="editingFlow.steps[activeStepIndex].modifier" class="search-input w-full" style="height: 32px;">
                  <option value="none">无</option>
                  <option value="ctrl">Ctrl</option>
                  <option value="shift">Shift</option>
                </select>
              </div>
            </div>

            <!-- 键盘按键 -->
            <div v-if="editingFlow.steps[activeStepIndex].action === 'key_press'" class="flex gap-sm align-center">
              <span class="caption">按键名:</span>
              <input type="text" v-model="editingFlow.steps[activeStepIndex].key" class="search-input" style="height: 32px; width: 120px;" placeholder="如 esc, enter">
            </div>

            <!-- 识图 -->
            <div v-if="editingFlow.steps[activeStepIndex].action === 'image_search'" class="grid-1col gap-sm">
              <div>
                <div class="caption mb-xs">图片路径:</div>
                <input type="text" v-model="editingFlow.steps[activeStepIndex].target" class="search-input w-full" style="height: 32px;">
              </div>
              <div class="flex gap-sm align-center mt-xs">
                <span class="caption">相似度(0-1):</span>
                <input type="number" step="0.1" v-model="editingFlow.steps[activeStepIndex].confidence" class="search-input" style="height: 32px; width: 80px;">
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
