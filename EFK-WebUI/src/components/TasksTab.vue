<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

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
  editingFlow.value = JSON.parse(JSON.stringify(flow))
}

const saveFlow = async () => {
  await props.apiCall('save_flow', editingFlow.value)
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

const addStep = (type) => {
  let step = { action: type }
  if (type === 'sleep') step.duration = 1000
  if (type === 'mouse_move') { step.x = 0; step.y = 0; }
  if (type === 'mouse_click') { step.button = 'left'; step.modifier = 'none'; }
  if (type === 'key_press') { step.key = 'esc'; }
  if (type === 'image_search') { step.target = ''; step.confidence = 0.8; }
  if (type === 'condition') { step.if = 'last_search_success'; step.then = []; }
  if (type === 'loop') { step.count = -1; step.children = []; }
  editingFlow.value.steps.push(step)
}

const removeStep = (index) => {
  editingFlow.value.steps.splice(index, 1)
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

      <section class="store-utility-card">
        <h3 class="body-strong mb-md">任务流程</h3>
        
        <!-- 步骤列表 -->
        <div v-for="(step, idx) in editingFlow.steps" :key="idx" class="mb-sm" style="background: var(--canvas-parchment); border-radius: 8px; padding: 12px; border: 1px solid var(--hairline);">
          <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div class="caption-strong text-primary">步骤 {{ idx + 1 }}: {{ step.action }}</div>
            <button class="button-pearl-capsule" style="padding: 4px 8px;" @click="removeStep(idx)">删除</button>
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
            <span class="caption">按键名(如 esc, a, enter):</span>
            <input type="text" v-model="step.key" class="search-input" style="height: 32px; width: 100px;">
          </div>

          <!-- 识图 -->
          <div v-if="step.action === 'image_search'" class="flex gap-sm align-center" style="flex-wrap: wrap;">
            <span class="caption">图片路径:</span>
            <input type="text" v-model="step.target" class="search-input w-full" style="height: 32px; margin-bottom: 8px;">
            <span class="caption">相似度:</span>
            <input type="number" step="0.1" v-model="step.confidence" class="search-input" style="height: 32px; width: 80px;">
          </div>
          
          <div v-if="step.action === 'condition'" class="caption muted">
            (如果上一步识图成功，则执行内部步骤 - 暂不支持界面内嵌套编辑，请手动配置 JSON)
          </div>
          <div v-if="step.action === 'loop'" class="caption muted">
            (循环执行内部步骤 - 暂不支持界面内嵌套编辑，请手动配置 JSON)
          </div>
        </div>

        <!-- 添加动作块 -->
        <div class="mt-md flex gap-sm" style="flex-wrap: wrap;">
          <button class="button-pearl-capsule" @click="addStep('sleep')">+ 延时</button>
          <button class="button-pearl-capsule" @click="addStep('mouse_move')">+ 鼠标移动</button>
          <button class="button-pearl-capsule" @click="addStep('mouse_click')">+ 鼠标点击</button>
          <button class="button-pearl-capsule" @click="addStep('key_press')">+ 键盘按键</button>
          <button class="button-pearl-capsule" @click="addStep('image_search')">+ 识图</button>
          <!-- 嵌套编辑比较复杂，为了保持极简 UI，目前可以用这些基础块组成线性流程 -->
        </div>
      </section>
    </div>
  </div>
</template>
