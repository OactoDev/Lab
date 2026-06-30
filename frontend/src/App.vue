<template>
  <div v-if="!authReady || authCheck === 'checking'" class="status-screen">Loading...</div>

  <Login v-else-if="!currentUser" />

  <div v-else-if="authCheck === 'denied'" class="status-screen denied">
    <p>This account ({{ currentUser.email }}) is not authorized to use this app.</p>
    <button @click="logout">Sign out</button>
  </div>

  <div v-else class="app-container">
    <header class="app-header">
      <div class="tabs">
        <button
          class="tab"
          :class="{ active: activeTab === 'documents' }"
          @click="activeTab = 'documents'"
        >
          Documents
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'ai-lab' }"
          @click="activeTab = 'ai-lab'"
        >
          AI Lab
        </button>
        <div class="header-account">
          <span class="account-email">{{ currentUser.email }}</span>
          <button class="logout-btn" @click="logout">Sign out</button>
        </div>
      </div>
    </header>

    <div v-if="activeTab === 'documents'" class="layout">
      <aside class="sidebar">
      <div class="sidebar-header">
        <span>COLLECTIONS</span>
        <button class="plus-btn" @click="showModal = true">+</button>
      </div>

      <ul class="collection-list">
        <li
          :class="{ active: selectedCollectionId === null }"
          @click="selectedCollectionId = null"
        >
          All Files
        </li>
        <li
          v-for="c in collections"
          :key="c.id"
          :class="{ active: selectedCollectionId === c.id }"
          @click="selectedCollectionId = c.id"
        >
          {{ c.name }}
        </li>
      </ul>

      <div class="sidebar-files">
        <div
          v-for="file in visibleFiles"
          :key="file.id"
          class="file-row"
          :class="{ active: openFile?.id === file.id }"
          @click="openFileInPanel(file)"
        >
          <span class="file-name" :title="file.original_filename">{{ file.original_filename }}</span>
          <span class="file-actions">
            <a href="#" @click.stop.prevent="downloadFile(file)">dl</a>
            <a href="#" @click.stop.prevent="deleteFile(file)">x</a>
          </span>
        </div>
        <div v-if="visibleFiles.length === 0" class="empty">no files</div>
      </div>
    </aside>

    <main class="main">
      <div v-if="!openFile">
        <h1>Upload a file</h1>

        <form @submit.prevent="uploadFile">
          <div class="field">
            <input id="file-input" type="file" @change="handleFileSelect" />
          </div>

          <div class="field">
            <label for="collection-select">Collection</label>
            <select id="collection-select" v-model="uploadCollectionId">
              <option :value="null">None</option>
              <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <button type="submit" :disabled="!selectedFile || isUploading">
            {{ isUploading ? "Uploading..." : "Upload" }}
          </button>
        </form>

        <p v-if="message">{{ message }}</p>
      </div>

      <div v-else>
        <PdfEditor
          v-if="openFileKind === 'pdf'"
          :file="openFile"
          @close="openFile = null"
          @saved="fetchFiles"
        />
        <TextEditor
          v-else-if="openFileKind === 'text'"
          :file="openFile"
          @close="openFile = null"
          @saved="fetchFiles"
        />
        <div v-else class="no-preview">
          <p>Preview not available for this file type.</p>
          <button @click="downloadFile(openFile)">Download</button>
          <button @click="openFile = null">Close</button>
        </div>
      </div>
    </main>
    </div>

    <div v-else-if="activeTab === 'ai-lab'" class="ai-lab-page">
      <h1>AI Lab</h1>
      <p>Coming soon...</p>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h2>New Collection</h2>
        <form @submit.prevent="createCollection">
          <div class="field">
            <label for="new-collection-name">Name</label>
            <input id="new-collection-name" v-model="newCollectionName" type="text" required />
          </div>
          <div class="field">
            <label for="new-collection-image">Image (optional)</label>
            <input id="new-collection-image" type="file" accept="image/*" @change="handleCollectionImageSelect" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeModal">Cancel</button>
            <button type="submit" :disabled="!newCollectionName">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PdfEditor from './components/PdfEditor.vue'
import TextEditor from './components/TextEditor.vue'
import Login from './components/Login.vue'
import { apiFetch } from './api'
import { currentUser, authReady, logout } from './auth'

const TEXT_EXTENSIONS = ['txt', 'md', 'csv', 'json', 'log', 'yml', 'yaml', 'js', 'py', 'html', 'css']

// 'checking' | 'authorized' | 'denied' — backed by /me, which enforces the
// ALLOWED_EMAILS allowlist. Authentication alone (any Google account) does
// not imply authorization, so this gate must be checked separately.
const authCheck = ref('checking')

const activeTab = ref('documents')

const collections = ref([])
const files = ref([])
const selectedCollectionId = ref(null)
const openFile = ref(null)

const selectedFile = ref(null)
const uploadCollectionId = ref(null)
const isUploading = ref(false)
const message = ref('')

const showModal = ref(false)
const newCollectionName = ref('')
const newCollectionImage = ref(null)

const visibleFiles = computed(() => {
  if (selectedCollectionId.value === null) return files.value
  return files.value.filter((f) => f.collection_id === selectedCollectionId.value)
})

const openFileKind = computed(() => {
  if (!openFile.value) return null
  const ext = openFile.value.original_filename.split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'pdf'
  if (TEXT_EXTENSIONS.includes(ext)) return 'text'
  return 'other'
})

const openFileInPanel = (file) => {
  openFile.value = file
}

const fetchCollections = async () => {
  const res = await apiFetch('/collections')
  if (res.ok) collections.value = await res.json()
}

const fetchFiles = async () => {
  const res = await apiFetch('/files')
  if (res.ok) files.value = await res.json()
}

const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0] || null
}

const uploadFile = async () => {
  if (!selectedFile.value) return

  isUploading.value = true
  message.value = ''

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  if (uploadCollectionId.value) {
    formData.append('collection_id', uploadCollectionId.value)
  }

  try {
    const res = await apiFetch('/upload', { method: 'POST', body: formData })
    if (res.ok) {
      message.value = `Uploaded "${selectedFile.value.name}"`
      selectedFile.value = null
      document.getElementById('file-input').value = ''
      await fetchFiles()
    } else {
      message.value = 'Upload failed'
    }
  } catch (e) {
    message.value = `Error: ${e.message}`
  } finally {
    isUploading.value = false
  }
}

const downloadFile = async (file) => {
  const res = await apiFetch(`/download/${file.id}`)
  if (!res.ok) return
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = file.original_filename
  a.click()
  URL.revokeObjectURL(url)
}

const deleteFile = async (file) => {
  if (!confirm(`Delete "${file.original_filename}"?`)) return
  const res = await apiFetch(`/files/${file.id}`, { method: 'DELETE' })
  if (res.ok) {
    if (openFile.value?.id === file.id) {
      openFile.value = null
    }
    await fetchFiles()
  }
}

const handleCollectionImageSelect = (event) => {
  newCollectionImage.value = event.target.files[0] || null
}

const closeModal = () => {
  showModal.value = false
  newCollectionName.value = ''
  newCollectionImage.value = null
}

const createCollection = async () => {
  if (!newCollectionName.value) return

  const formData = new FormData()
  formData.append('name', newCollectionName.value)
  if (newCollectionImage.value) {
    formData.append('image', newCollectionImage.value)
  }

  const res = await apiFetch('/collections', { method: 'POST', body: formData })
  if (res.ok) {
    await fetchCollections()
    closeModal()
  }
}

// Any Google account can authenticate, but only allowlisted emails are
// authorized. Confirm via /me (which enforces ALLOWED_EMAILS) before loading
// any data or rendering the app shell.
watch(
  currentUser,
  async (user) => {
    if (!user) {
      authCheck.value = 'checking'
      collections.value = []
      files.value = []
      openFile.value = null
      return
    }

    authCheck.value = 'checking'
    const res = await apiFetch('/me')
    if (res.ok) {
      authCheck.value = 'authorized'
      fetchCollections()
      fetchFiles()
    } else {
      authCheck.value = 'denied'
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.status-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.status-screen.denied {
  flex-direction: column;
  gap: 16px;
  text-align: center;
  padding: 24px;
}

.status-screen.denied button {
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 8px 16px;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  border-bottom: 1px solid #000;
}

.tabs {
  display: flex;
  gap: 0;
  align-items: stretch;
}

.header-account {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-left: 1px solid #000;
  font-size: 13px;
}

.account-email {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.logout-btn {
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 4px 10px;
}

.tab {
  flex: 1;
  padding: 12px;
  border: none;
  border-right: 1px solid #000;
  background: #fff;
  color: #000;
  cursor: pointer;
  font-weight: normal;
  text-align: center;
}

.tab:last-child {
  border-right: none;
}

.tab.active {
  font-weight: bold;
  text-decoration: underline;
}

.layout {
  display: flex;
  flex: 1;
}

.ai-lab-page {
  flex: 1;
  padding: 24px;
}

.sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid #000;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #000;
  font-weight: bold;
  letter-spacing: 0.05em;
}

.plus-btn {
  background: none;
  border: 1px solid #000;
  width: 20px;
  height: 20px;
  line-height: 1;
  font-size: 14px;
}

.collection-list {
  list-style: none;
  border-bottom: 1px solid #000;
}

.collection-list li {
  padding: 8px 12px;
  cursor: pointer;
}

.collection-list li.active {
  font-weight: bold;
  text-decoration: underline;
}

.collection-list li:hover {
  text-decoration: underline;
}

.sidebar-files {
  flex: 1;
  overflow-y: auto;
}

.file-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  font-size: 13px;
  gap: 6px;
  cursor: pointer;
}

.file-row:hover,
.file-row.active {
  text-decoration: underline;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.file-actions a {
  color: #000;
}

.empty {
  padding: 12px;
  font-size: 13px;
  color: #000;
}

.main {
  flex: 1;
  padding: 24px;
  min-width: 0;
}

.no-preview {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.field {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  font-size: 13px;
}

select,
input[type='text'] {
  border: 1px solid #000;
  padding: 6px;
  background: #fff;
  color: #000;
}

button {
  border: 1px solid #000;
  background: #fff;
  color: #000;
  padding: 6px 12px;
}

button:disabled {
  opacity: 0.4;
  cursor: default;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: #fff;
  border: 1px solid #000;
  padding: 20px;
  width: 320px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
