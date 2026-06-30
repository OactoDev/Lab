<template>
  <div class="text-editor">
    <div class="toolbar">
      <span class="file-title">{{ file.original_filename }}</span>
      <span class="spacer"></span>
      <button @click="save" :disabled="isSaving">{{ isSaving ? 'Saving...' : 'Save' }}</button>
      <button @click="$emit('close')">Close</button>
    </div>

    <p v-if="isLoading">Loading...</p>
    <textarea v-else v-model="content" class="text-area" spellcheck="false"></textarea>

    <p v-if="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const API_BASE_URL = 'http://localhost:8000'

const props = defineProps({
  file: { type: Object, required: true },
})

const emit = defineEmits(['close', 'saved'])

const content = ref('')
const isLoading = ref(true)
const isSaving = ref(false)
const message = ref('')

const load = async () => {
  isLoading.value = true
  const res = await fetch(`${API_BASE_URL}/download/${props.file.stored_filename}`)
  content.value = await res.text()
  isLoading.value = false
}

const save = async () => {
  isSaving.value = true
  message.value = ''

  const blob = new Blob([content.value], { type: 'text/plain' })
  const formData = new FormData()
  formData.append('file', blob, props.file.original_filename)

  try {
    const res = await fetch(`${API_BASE_URL}/files/${props.file.id}`, {
      method: 'PUT',
      body: formData,
    })
    if (res.ok) {
      message.value = 'Saved'
      emit('saved')
    } else {
      message.value = 'Save failed'
    }
  } catch (e) {
    message.value = `Error: ${e.message}`
  } finally {
    isSaving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.text-editor {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.file-title {
  font-weight: bold;
}

.spacer {
  flex: 1;
}

button {
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 6px 12px;
}

.text-area {
  flex: 1;
  width: 100%;
  border: 1px solid #000;
  padding: 12px;
  font-family: monospace;
  font-size: 14px;
  resize: none;
  color: #000;
  background: #fff;
}
</style>
