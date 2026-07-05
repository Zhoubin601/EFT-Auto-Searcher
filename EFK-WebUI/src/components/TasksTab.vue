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
}

const editFlow = (flow) => {
  // 注入唯一 ID 用于拖拽
  const f = JSON.parse(JSON.stringify(flow))
  if (f.steps) {
    f.steps.forEach(s => {
      if (!s._id) s._id = Date.now() + Math.random()
    })
  } else {
    f.steps = []
  }
  editingFlow.value = f
}

const saveFlow = async () => {
  // 去除内部使用的 _id
  const f = JSON.parse(JSON.stringify(editingFlow.value))
  f.steps.forEach(s => {
    delete s._id
  })
  await props.apiCall('save_flow', f)
  editingFlow.value = null
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
  editingFlow.value.steps.splice(index, 1)
}

// 底部可用组件库
const availableComponents = ref([
  { action: 'sleep', name: '延时' },
  { action: 'mouse_move', name: '鼠标移动' },
  { action: 'mouse_click', name: '鼠标点击' },
  { action: 'key_press', name: '键盘按键' },
  { action: 'image_search', name: '识图' }
])

// 拖拽克隆生成实际的数据节点
const cloneComponent = (cmp) => {
  let step = { action: cmp.action, _id: Date.now() + Math.random() }
  if (cmp.action === 'sleep') step.duration = 1000
  if (cmp.action === 'mouse_move') { step.x = 0; step.y = 0; }
  if (cmp.action === 'mouse_click') { step.button = 'left'; step.modifier = 'none'; }
  if (cmp.action === 'key_press') { step.key = 'esc'; }
  if (cmp.action === 'image_search') { step.target = ''; step.confidence = 0.8; }
  return step
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

    <!-- 编辑视图 (拖拽上下分栏) -->
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

      <!-- 上方：流程画布 -->
      <section class="store-utility-card mb-md">
        <h3 class="body-strong mb-md">流程画布 <span class="caption muted font-normal ml-sm">(可拖拽排序)</span></h3>
        
        <draggable
          v-model="editingFlow.steps"
          group="flow"
          item-key="_id"
          animation="200"
          style="min-height: 100px; border: 2px dashed var(--hairline); padding: 12px; border-radius: 12px;"
        >
          <template #item="{ element: step, index }">
            <div class="mb-sm cursor-move" style="background: var(--canvas-parchment); border-radius: 8px; padding: 12px; border: 1px solid var(--hairline);">
              <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div class="caption-strong text-primary flex align-center gap-xs">
                  <span style="font-size: 16px;">≡</span> 步骤 {{ index + 1 }}: {{ step.action }}
                </div>
                <button class="button-pearl-capsule" style="padding: 4px 8px;" @click="removeStep(index)">删除</button>
              </div>

              <!-- 延时 -->
              <div v-if="step.action === 'sleep'" class="flex gap-sm align-center">
                <span class="caption">延时(毫秒):</span>
                <input type="number" v-model="step.duration" class="search-input" style="height: 32px; width: 100px;">
              </div>

              <!-- 鼠标移动 -->
              <div v-if="step.action === 'mouse_move'" class="flex gap-sm align-center">
                <span class="caption">X:</span>
                <input type="number" v-model="step.x" class="search-input" style="height: 32px; width: 80px;">
                <span class="caption">Y:</span>
                <input type="number" v-model="step.y" class="search-input" style="height: 32px; width: 80px;">
              </div>

              <!-- 鼠标点击 -->
              <div v-if="step.action === 'mouse_click'" class="flex gap-sm align-center">
                <span class="caption">按键:</span>
                <select v-model="step.button" class="search-input" style="height: 32px; width: 100px;">
                  <option value="left">左键</option>
                  <option value="right">右键</option>
                </select>
                <span class="caption">修饰键:</span>
                <select v-model="step.modifier" class="search-input" style="height: 32px; width: 100px;">
                  <option value="none">无</option>
                  <option value="ctrl">Ctrl</option>
                  <option value="shift">Shift</option>
                </select>
              </div>

              <!-- 键盘按键 -->
              <div v-if="step.action === 'key_press'" class="flex gap-sm align-center">
                <span class="caption">按键名(如 esc, a):</span>
                <input type="text" v-model="step.key" class="search-input" style="height: 32px; width: 100px;">
              </div>

              <!-- 识图 -->
              <div v-if="step.action === 'image_search'" class="flex gap-sm align-center" style="flex-wrap: wrap;">
                <span class="caption">图片路径:</span>
                <input type="text" v-model="step.target" class="search-input w-full" style="height: 32px; margin-bottom: 8px;">
                <span class="caption">相似度:</span>
                <input type="number" step="0.1" v-model="step.confidence" class="search-input" style="height: 32px; width: 80px;">
              </div>
            </div>
          </template>
          <!-- 空状态占位 -->
          <template #header v-if="editingFlow.steps.length === 0">
            <div class="text-center caption muted" style="line-height: 80px;">
              拖拽下方组件到这里
            </div>
          </template>
        </draggable>
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
  </div>
</template>

<style scoped>
.cursor-move {
  cursor: grab;
}
.cursor-move:active {
  cursor: grabbing;
}
</style>
