<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const state = ref({
  is_running: false,
  trigger_key: 'V',
  scan_region: null,
  is_recording_key: false,
  is_setting_area: false,
  is_setting_ammo_pos: false,
  is_ammo_running: false,
  ammo_box_start: null,
  ammo_col_gap: 0,
  ammo_row_gap: 0,
  ammo_target_pos: null,
  icon_files: []
})

const currentTab = ref('home')

const inputConfidence = ref(0.8)
const inputCooldown = ref(0.1)
const inputAmmoCount = ref(1)

const selectedImage = ref(-1)

let pywebviewReady = false
let pollInterval = null
let initialized = false

const apiCall = async (methodName, ...args) => {
  if (window.pywebview && window.pywebview.api) {
    return await window.pywebview.api[methodName](...args)
  }
}

const updateState = async () => {
  if (window.pywebview && window.pywebview.api) {
    pywebviewReady = true
    const newState = await apiCall('get_state')
    if (newState) {
      state.value.is_running = newState.is_running
      state.value.trigger_key = newState.trigger_key
      state.value.scan_region = newState.scan_region
      state.value.is_recording_key = newState.is_recording_key
      state.value.is_setting_area = newState.is_setting_area
      state.value.is_setting_ammo_pos = newState.is_setting_ammo_pos
      state.value.is_ammo_running = newState.is_ammo_running
      state.value.ammo_box_start = newState.ammo_box_start
      state.value.ammo_col_gap = newState.ammo_col_gap
      state.value.ammo_row_gap = newState.ammo_row_gap
      state.value.ammo_target_pos = newState.ammo_target_pos
      state.value.icon_files = newState.icon_files

      if (!initialized) {
        inputConfidence.value = newState.confidence
        inputCooldown.value = newState.cooldown
        inputAmmoCount.value = newState.ammo_click_count
        initialized = true
      }
    }
  }
}

onMounted(() => {
  pollInterval = setInterval(updateState, 300)
  
  window.addEventListener('pywebviewready', () => {
    pywebviewReady = true
    updateState()
  })
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

const updateConfig = () => apiCall('update_cfg', inputConfidence.value, inputCooldown.value)
const startRecordKey = () => apiCall('start_record_key')
const startArea = () => apiCall('start_area')
const resetArea = () => apiCall('reset_area')

const saveAmmoCount = () => apiCall('save_ammo_count', inputAmmoCount.value)
const toggleAmmoPosSetting = () => apiCall('toggle_ammo_pos_setting')
const startAmmoBatch = () => apiCall('start_ammo_batch')
const stopAmmoBatch = () => apiCall('stop_ammo_batch')

const addImage = () => apiCall('add_image')
const autoAddImages = () => apiCall('auto_add_images')
const removeImage = () => {
  if (selectedImage.value >= 0) {
    apiCall('remove_image', selectedImage.value)
    selectedImage.value = -1
  }
}

const restoreAll = async () => {
  await apiCall('restore_all')
  initialized = false
}
const exitProgram = () => apiCall('exit_program')
</script>

<template>
  <!-- 拖拽标题栏 -->
  <div class="titlebar pywebview-drag-region">
    <div class="titlebar-title">EFT Auto Searcher</div>
  </div>

  <div class="app-layout">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <button class="nav-item" :class="{ active: currentTab === 'home' }" @click="currentTab = 'home'">首页</button>
      <button class="nav-item" :class="{ active: currentTab === 'settings' }" @click="currentTab = 'settings'">基本参数</button>
      <button class="nav-item" :class="{ active: currentTab === 'ammo' }" @click="currentTab = 'ammo'">弹药装填</button>
      <button class="nav-item" :class="{ active: currentTab === 'images' }" @click="currentTab = 'images'">图像管理</button>
      <div style="flex: 1"></div>
      <button class="nav-item text-red" @click="exitProgram">退出程序</button>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <div class="content-wrapper">
        
        <!-- 首页 (Home) -->
        <div v-if="currentTab === 'home'">
          <section class="store-utility-card text-center mb-xl">
            <h2 class="caption-strong muted">全图搜查状态</h2>
            <div v-if="state.is_running" class="display-md text-green mt-xs">▶ 运行中</div>
            <div v-else class="display-md text-red mt-xs">■ 已停止</div>
            <div class="caption muted mt-sm">快捷键：{{ state.trigger_key.toUpperCase() }}</div>
          </section>

          <section class="store-utility-card text-center mb-xl">
            <h2 class="caption-strong muted">弹药装填状态</h2>
            <div v-if="state.is_ammo_running" class="display-md text-green mt-xs">▶ 装填中</div>
            <div v-else class="display-md text-red mt-xs">■ 未运行</div>
            <div class="caption muted mt-sm">启动：F5 / 停止：F12</div>
          </section>

          <section class="store-utility-card mt-xl">
            <h3 class="body-strong mb-md">关于此工具</h3>
            <p class="body muted">
              此工具分为两个核心模块：<br><br>
              <strong>1. 全图搜查：</strong>根据【图像管理】中的图片模板，在指定范围内持续搜索并自动点击。<br><br>
              <strong>2. 弹药装填：</strong>根据 7×7 网格布局，自动双击弹药箱并将散装弹药批量填入指定位置。
            </p>
          </section>
        </div>

        <!-- 基本参数 (Settings) -->
        <div v-if="currentTab === 'settings'">
          <h2 class="display-md mb-lg">基本参数</h2>
          
          <section class="store-utility-card mb-xl">
            <h3 class="body-strong mb-md">运行配置</h3>
            <div class="form-row">
              <label class="body">匹配精度 (0.5-0.9)</label>
              <input type="text" v-model="inputConfidence" class="search-input" style="width: 80px; text-align: center;">
            </div>
            <div class="form-row mt-sm">
              <label class="body">点击间隔 (秒)</label>
              <input type="text" v-model="inputCooldown" class="search-input" style="width: 80px; text-align: center;">
            </div>
            <button class="button-primary mt-lg w-full" @click="updateConfig">更新并保存参数</button>
          </section>

          <section class="store-utility-card mb-xl">
            <h3 class="body-strong mb-md">操作区域</h3>
            <div class="caption-strong mb-sm">
              当前热键: <span class="text-primary">{{ state.trigger_key.toUpperCase() }}</span>
            </div>
            <button class="button-pearl-capsule mb-md w-full" @click="startRecordKey">
              {{ state.is_recording_key ? '请按下新热键...' : '点击修改启动热键' }}
            </button>
            
            <div class="caption-strong mt-md mb-sm" id="lbl-area">
              当前范围: {{ state.scan_region ? `${state.scan_region.width}x${state.scan_region.height}` : '全屏' }}
            </div>
            <div class="flex gap-sm">
              <button class="button-dark-utility flex-1" @click="startArea">
                {{ state.is_setting_area ? '设置中...' : '划定范围(4次F1)' }}
              </button>
              <button class="button-secondary-pill flex-1" @click="resetArea">还原全屏</button>
            </div>
          </section>

          <div class="text-center mt-xl">
            <button class="button-pearl-capsule" @click="restoreAll">一键恢复所有默认设置</button>
          </div>
        </div>

        <!-- 弹药装填 (Ammo Batch) -->
        <div v-if="currentTab === 'ammo'">
          <h2 class="display-md mb-lg">弹药装填</h2>
          
          <section class="store-utility-card mb-xl">
            <h3 class="body-strong mb-md">7×7 网格装填</h3>
            <div class="caption muted mb-md" style="word-wrap: break-word; line-height: 1.8;">
              • 起始箱: {{ state.ammo_box_start ? '已设' : '未设置' }}<br>
              • 横纵间距: {{ state.ammo_col_gap }} / {{ state.ammo_row_gap }}<br>
              • 目标弹药位: {{ state.ammo_target_pos ? '已设' : '未设置' }}
            </div>
            
            <div class="form-row mb-md">
              <label class="body">每个箱子放置次数：</label>
              <div class="flex gap-sm align-center">
                <input type="text" v-model="inputAmmoCount" class="search-input" style="width: 60px; text-align: center;">
                <button class="button-pearl-capsule" @click="saveAmmoCount">保存</button>
              </div>
            </div>

            <button class="button-primary w-full mb-md" @click="toggleAmmoPosSetting">
              {{ state.is_setting_ammo_pos ? '坐标采集完毕 (点击关闭)' : '开启坐标采集 (F1-F4)' }}
            </button>

            <div class="store-utility-card mb-lg" style="background-color: var(--canvas-parchment);">
              <div class="caption muted">
                <strong>操作指引 (需先开启采集)：</strong><br><br>
                <span class="text-primary">【F1】</span> 第一个弹药箱位置<br>
                <span class="text-primary">【F2】</span> 横向间距（点右侧弹药箱）<br>
                <span class="text-primary">【F3】</span> 纵向间距（点下排弹药箱）<br>
                <span class="text-primary">【F4】</span> 弹药放置的目标位置
              </div>
            </div>

            <div class="grid-2col gap-sm">
              <button class="button-primary" @click="startAmmoBatch">启动批量 (F5)</button>
              <button class="button-dark-utility" @click="stopAmmoBatch">停止批量 (F12)</button>
            </div>
          </section>
        </div>

        <!-- 图像管理 (Images) -->
        <div v-if="currentTab === 'images'">
          <h2 class="display-md mb-lg">图像管理</h2>
          
          <section class="store-utility-card mb-xl">
            <h3 class="body-strong mb-xs">识别库</h3>
            <p class="caption muted mb-md">所有的图像模板将被自动保存。OpenCV 将会在界面中搜寻这些图案。</p>
            
            <select v-model="selectedImage" class="search-input w-full mb-md" size="6" style="height: 180px; padding: 12px; border-radius: 11px;">
              <option v-for="(img, idx) in state.icon_files" :key="idx" :value="idx">
                {{ img.split('\\').pop().split('/').pop() }}
              </option>
            </select>
            
            <div class="grid-2col gap-sm">
              <button class="button-primary" @click="autoAddImages">自动加载 Graph 图库</button>
              <button class="button-secondary-pill" @click="addImage">手动添加单张</button>
            </div>
            <div class="mt-sm">
              <button class="button-dark-utility w-full" @click="removeImage">删除选中项</button>
            </div>
          </section>
        </div>

      </div>
    </div>
  </div>
</template>
