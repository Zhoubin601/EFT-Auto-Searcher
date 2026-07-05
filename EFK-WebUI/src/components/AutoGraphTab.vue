<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  apiCall: { type: Function, required: true }
})

const libs = ref([])
const newLibName = ref('')
const selectedLib = ref(null)
const selectedLibFiles = ref([])
const isCreatingLib = ref(false)

const loadLibs = async () => {
  const result = await props.apiCall('get_autograph_libs')
  if (result) libs.value = result
}

const createLib = async () => {
  if (!newLibName.value) return
  await props.apiCall('create_autograph_lib', newLibName.value)
  newLibName.value = ''
  isCreatingLib.value = false
  loadLibs()
}

const deleteLib = async (name) => {
  await props.apiCall('delete_autograph_lib', name)
  if (selectedLib.value === name) {
    selectedLib.value = null
    selectedLibFiles.value = []
  }
  loadLibs()
}

const selectLib = async (name) => {
  selectedLib.value = name
  const files = await props.apiCall('get_autograph_lib_files', name)
  if (files) selectedLibFiles.value = files
}

const importImages = async () => {
  if (!selectedLib.value) return
  const success = await props.apiCall('import_to_autograph_lib', selectedLib.value)
  if (success) {
    selectLib(selectedLib.value)
  }
}

onMounted(() => {
  loadLibs()
})
</script>

<template>
  <div>
    <div class="grid-2col gap-md" style="grid-template-columns: 240px 1fr;">
      <!-- 左侧：图库列表 -->
      <section class="store-utility-card">
        <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 class="body-strong">所有图库</h3>
          <button class="button-pearl-capsule" style="padding: 4px 12px; font-size: 13px;" @click="isCreatingLib = true">+ 新建</button>
        </div>
        
        <div v-if="libs.length === 0" class="caption muted text-center mt-md">
          暂无图库
        </div>
        
        <div class="grid-1col gap-xs">
          <div v-for="lib in libs" :key="lib"
               class="flex align-center"
               style="justify-content: space-between; padding: 12px; border-radius: 8px; border: 1px solid var(--hairline); cursor: pointer; transition: all 0.2s;"
               :style="{ backgroundColor: selectedLib === lib ? 'var(--primary)' : 'var(--canvas)', color: selectedLib === lib ? 'white' : 'var(--ink)' }"
               @click="selectLib(lib)">
            <span class="body-strong" style="word-break: break-all;">{{ lib }}</span>
            <button class="button-pearl-capsule" style="padding: 2px 8px; font-size: 12px; flex-shrink: 0;" :style="{ color: selectedLib === lib ? 'var(--ink)' : '#ff3b30' }" @click.stop="deleteLib(lib)">删除</button>
          </div>
        </div>
      </section>

      <!-- 右侧：图库详情 -->
      <section class="store-utility-card" v-if="selectedLib">
        <div class="flex" style="justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 class="body-strong">图库: {{ selectedLib }}</h3>
          <button class="button-primary" style="padding: 6px 16px;" @click="importImages">一键导入图片</button>
        </div>

        <p class="caption muted mb-md">当在自动化任务中选用该图库时，引擎会尝试匹配库中的任意一张图片（或逻辑）。</p>

        <div v-if="selectedLibFiles.length === 0" class="caption muted text-center mt-xl">
          该图库为空，请点击右上角导入图片。
        </div>

        <div class="image-list-container">
          <div v-for="(img, idx) in selectedLibFiles" :key="idx" class="image-list-item" style="cursor: default; word-break: break-all;">
            {{ img }}
          </div>
        </div>
      </section>
      <section class="store-utility-card" v-else>
        <div class="caption muted text-center mt-xl" style="height: 100%; min-height: 200px; display: flex; align-items: center; justify-content: center;">
          请在左侧选择或新建一个图库
        </div>
      </section>
    </div>

    <!-- 弹窗：新建图库 -->
    <Teleport to="body">
      <div v-if="isCreatingLib" class="modal-overlay" @click.self="isCreatingLib = false">
        <div class="modal-content">
          <h3 class="body-strong mb-md">新建自动化图库</h3>
          <div class="caption mb-xs">图库名称:</div>
          <input type="text" v-model="newLibName" class="search-input w-full mb-md" style="height: 36px;" placeholder="建议使用英文或数字" @keyup.enter="createLib">
          
          <div class="flex gap-sm">
            <button class="button-pearl-capsule flex-1" @click="isCreatingLib = false">取消</button>
            <button class="button-primary flex-1" @click="createLib">确定</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.image-list-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.image-list-item {
  background: var(--canvas-parchment);
  border: 1px solid var(--hairline);
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--ink);
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
  width: 300px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.2);
  border: 1px solid var(--hairline);
}
</style>
