<script setup>
import draggable from 'vuedraggable'

const props = defineProps({
  steps: { type: Array, required: true },
  activeStepId: { type: String, default: null },
  getStepName: { type: Function, required: true }
})

// Due to Vue recursive component resolution, it might need to reference itself by name
defineOptions({ name: 'NestedDraggable' })

const emit = defineEmits(['select-step', 'remove-step'])

const onConditionChange = (e, element) => {
  if (e.added && element.condition_list.length > 1) {
    // Keep only the most recently added item
    const newItem = element.condition_list.pop()
    element.condition_list = [newItem]
  }
}
</script>

<template>
  <draggable
    :list="steps"
    group="flow"
    item-key="_id"
    animation="200"
    class="horizontal-flow"
  >
    <template #item="{ element, index }">
      <div class="flow-step-item">
        
        <!-- Normal Step -->
        <div v-if="!['loop', 'condition'].includes(element.action)" 
             class="flow-step-box" 
             :class="{ 'active': activeStepId === element._id }" 
             @click.stop="emit('select-step', element._id)">
          <div class="step-delete" @click.stop="emit('remove-step', element._id)">×</div>
          <div class="caption-strong text-primary">{{ getStepName(element.action) }}</div>
        </div>

        <!-- Container Step -->
        <div v-else 
             class="nested-container-box" 
             :class="{ 'active': activeStepId === element._id }" 
             @click.stop="emit('select-step', element._id)">
          <div class="step-delete" @click.stop="emit('remove-step', element._id)">×</div>
          
          <div class="nested-header">
            <span class="body-strong">{{ getStepName(element.action) }}</span>
            <span v-if="element.action === 'loop'" class="caption muted ml-xs">
              ({{ element.count === -1 ? '无限循环' : element.count + '次' }})
            </span>
          </div>
          
          <div class="nested-body flex">
            <!-- 条件插槽 -->
            <div class="condition-slot-wrapper mr-md">
              <div class="caption muted mb-xs text-center" style="font-size: 11px;">条件插槽 (可选)</div>
              <draggable
                v-model="element.condition_list"
                group="flow"
                @change="e => onConditionChange(e, element)"
                item-key="_id"
                animation="200"
                class="condition-slot"
              >
                <template #item="{ element: condEl }">
                  <div class="flow-step-box mini" 
                       :class="{ 'active': activeStepId === condEl._id }" 
                       @click.stop="emit('select-step', condEl._id)">
                    <div class="step-delete" @click.stop="emit('remove-step', condEl._id)">×</div>
                    <div class="caption-strong text-primary">{{ getStepName(condEl.action) }}</div>
                  </div>
                </template>
                <template #header v-if="!element.condition_list || element.condition_list.length === 0">
                  <div class="empty-slot">拖入判定</div>
                </template>
              </draggable>
            </div>
            
            <!-- 子流程 -->
            <div class="child-flow-wrapper">
              <div class="caption muted mb-xs" style="font-size: 11px;">执行流</div>
              <div class="child-flow-container">
                <NestedDraggable 
                  :steps="element.action === 'loop' ? element.children : element.then"
                  :activeStepId="activeStepId"
                  :getStepName="getStepName"
                  @select-step="id => emit('select-step', id)"
                  @remove-step="id => emit('remove-step', id)"
                />
              </div>
            </div>
          </div>
        </div>

      </div>
    </template>
    <template #header v-if="steps.length === 0">
      <div class="empty-placeholder">拖放组件到这里</div>
    </template>
  </draggable>
</template>

<style scoped>
/* Normal Box styles (adapted from TasksTab) */
.horizontal-flow { display: flex; flex-wrap: nowrap; align-items: center; min-height: 80px; }
.flow-step-item { display: flex; align-items: center; flex-shrink: 0; }
.flow-step-item::after { content: '→'; margin: 0 16px; color: var(--ink-muted-48); font-weight: 600; font-size: 20px; }
.horizontal-flow > *:last-child::after { display: none; }

.flow-step-box { position: relative; width: 80px; height: 80px; background: var(--canvas); border: 2px solid var(--hairline); border-radius: 12px; display: flex; justify-content: center; align-items: center; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
.flow-step-box:hover { border-color: var(--primary); transform: translateY(-2px); }
.flow-step-box.active { border-color: var(--primary); background: rgba(0, 102, 204, 0.05); }

.flow-step-box.mini { width: 70px; height: 70px; border-radius: 8px; }

.step-delete { position: absolute; top: -8px; right: -8px; width: 20px; height: 20px; background: #ff3b30; color: white; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 14px; line-height: 1; cursor: pointer; opacity: 0; transition: opacity 0.2s; z-index: 10; }
.flow-step-box:hover .step-delete, .nested-container-box:hover > .step-delete { opacity: 1; }
.step-delete:hover { transform: scale(1.1); }

/* Nested Container */
.nested-container-box { position: relative; background: var(--canvas-parchment); border: 2px dashed var(--hairline); border-radius: 16px; padding: 16px; display: flex; flex-direction: column; cursor: pointer; transition: all 0.2s; }
.nested-container-box:hover { border-color: var(--primary); }
.nested-container-box.active { border-color: var(--primary); background: rgba(0, 102, 204, 0.05); }
.nested-header { margin-bottom: 12px; border-bottom: 1px solid var(--hairline); padding-bottom: 8px; }

/* Condition Slot */
.condition-slot { width: 80px; min-height: 80px; border: 2px dashed #ff9500; border-radius: 12px; background: rgba(255,149,0,0.05); padding: 4px; }
.empty-slot { font-size: 11px; color: #ff9500; font-weight: 600; text-align: center; margin-top: 25px; }

/* Child Flow */
.child-flow-container { background: var(--canvas); border-radius: 12px; border: 1px solid var(--hairline); padding: 12px; min-width: 120px; overflow-x: auto; display: flex; }
.empty-placeholder { color: var(--ink-muted-48); font-size: 13px; padding: 0 16px; font-weight: 600; }
</style>
