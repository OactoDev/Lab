<template>
  <div class="pdf-editor">
    <div class="toolbar">
      <span class="file-title">{{ file.original_filename }}</span>
      <button :class="{ active: mode === 'draw' }" @click="mode = mode === 'draw' ? 'none' : 'draw'">
        Draw
      </button>
      <button :class="{ active: mode === 'text' }" @click="mode = mode === 'text' ? 'none' : 'text'">
        Add Text
      </button>
      <button @click="clearPage">Clear Page</button>
      <span class="spacer"></span>
      <button @click="save" :disabled="isSaving || isLoading">{{ isSaving ? 'Saving...' : 'Save' }}</button>
      <button @click="$emit('close')">Close</button>
    </div>

    <p v-if="isLoading">Loading PDF...</p>
    <p v-if="message">{{ message }}</p>

    <div class="pages" v-show="!isLoading">
      <div
        v-for="i in pageIndices"
        :key="i"
        class="page"
        :style="{ width: (pageSizes[i]?.width || 0) + 'px', height: (pageSizes[i]?.height || 0) + 'px' }"
      >
        <canvas :ref="(el) => (renderCanvases[i] = el)"></canvas>
        <canvas
          :ref="(el) => (overlayCanvases[i] = el)"
          class="overlay"
          :class="{ 'mode-draw': mode === 'draw', 'mode-text': mode === 'text' }"
          @pointerdown="onPointerDown(i, $event)"
          @pointermove="onPointerMove(i, $event)"
          @pointerup="onPointerUp(i, $event)"
          @pointerleave="onPointerUp(i, $event)"
          @click="onCanvasClick(i, $event)"
        ></canvas>
        <textarea
          v-for="ann in textAnnotations.filter((a) => a.pageIndex === i)"
          :key="ann.id"
          v-model="ann.text"
          class="text-annotation"
          :style="{ left: ann.x + 'px', top: ann.y + 'px' }"
          :ref="(el) => el && ann.id === lastAnnotationId && el.focus()"
        ></textarea>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf'
import pdfjsWorker from 'pdfjs-dist/legacy/build/pdf.worker?url'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const SCALE = 1.3

const props = defineProps({
  file: { type: Object, required: true },
})

const emit = defineEmits(['close', 'saved'])

const isLoading = ref(true)
const isSaving = ref(false)
const message = ref('')
const mode = ref('none')

const numPages = ref(0)
const pageIndices = computed(() => Array.from({ length: numPages.value }, (_, i) => i))
const pageSizes = reactive([])
const renderCanvases = reactive([])
const overlayCanvases = reactive([])
const textAnnotations = ref([])
const lastAnnotationId = ref(null)

let drawing = false
let nextAnnotationId = 1

const fetchPdfBytes = async () => {
  const res = await fetch(`${API_BASE_URL}/download/${props.file.stored_filename}`)
  return await res.arrayBuffer()
}

const loadAndRender = async () => {
  isLoading.value = true
  message.value = ''
  textAnnotations.value = []

  const bytes = await fetchPdfBytes()
  const pdfDoc = await pdfjsLib.getDocument({ data: bytes }).promise
  numPages.value = pdfDoc.numPages
  pageSizes.length = 0
  renderCanvases.length = 0
  overlayCanvases.length = 0

  for (let i = 0; i < numPages.value; i++) {
    const page = await pdfDoc.getPage(i + 1)
    const viewport = page.getViewport({ scale: SCALE })
    pageSizes[i] = { width: viewport.width, height: viewport.height }
  }

  await new Promise((resolve) => setTimeout(resolve, 0))

  for (let i = 0; i < numPages.value; i++) {
    const page = await pdfDoc.getPage(i + 1)
    const viewport = page.getViewport({ scale: SCALE })

    const canvas = renderCanvases[i]
    canvas.width = viewport.width
    canvas.height = viewport.height
    const ctx = canvas.getContext('2d')
    await page.render({ canvasContext: ctx, viewport }).promise

    const overlay = overlayCanvases[i]
    overlay.width = viewport.width
    overlay.height = viewport.height
  }

  isLoading.value = false
}

const onPointerDown = (i, event) => {
  if (mode.value !== 'draw') return
  drawing = true
  const ctx = overlayCanvases[i].getContext('2d')
  ctx.strokeStyle = '#000'
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(event.offsetX, event.offsetY)
}

const onPointerMove = (i, event) => {
  if (mode.value !== 'draw' || !drawing) return
  const ctx = overlayCanvases[i].getContext('2d')
  ctx.lineTo(event.offsetX, event.offsetY)
  ctx.stroke()
}

const onPointerUp = () => {
  drawing = false
}

const onCanvasClick = (i, event) => {
  if (mode.value !== 'text') return
  const id = nextAnnotationId++
  textAnnotations.value.push({
    id,
    pageIndex: i,
    x: event.offsetX,
    y: event.offsetY,
    text: '',
  })
  lastAnnotationId.value = id
}

const clearPage = () => {
  pageIndices.value.forEach((i) => {
    const overlay = overlayCanvases[i]
    if (overlay) {
      overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height)
    }
  })
  textAnnotations.value = []
}

const save = async () => {
  isSaving.value = true
  message.value = ''

  try {
    const bytes = await fetchPdfBytes()
    const pdfLibDoc = await PDFDocument.load(bytes)
    const font = await pdfLibDoc.embedFont(StandardFonts.Helvetica)
    const pages = pdfLibDoc.getPages()

    for (let i = 0; i < pages.length; i++) {
      const pdfPage = pages[i]
      const { width: pw, height: ph } = pdfPage.getSize()

      const overlay = overlayCanvases[i]
      if (overlay) {
        const dataUrl = overlay.toDataURL('image/png')
        const pngBytes = await fetch(dataUrl).then((r) => r.arrayBuffer())
        const pngImage = await pdfLibDoc.embedPng(pngBytes)
        pdfPage.drawImage(pngImage, { x: 0, y: 0, width: pw, height: ph })
      }

      const annotationsForPage = textAnnotations.value.filter((a) => a.pageIndex === i && a.text.trim())
      for (const ann of annotationsForPage) {
        const fontSize = 14
        const pdfX = ann.x / SCALE
        const pdfY = ph - ann.y / SCALE
        pdfPage.drawText(ann.text, {
          x: pdfX,
          y: pdfY,
          size: fontSize,
          font,
          color: rgb(0, 0, 0),
        })
      }
    }

    const finalBytes = await pdfLibDoc.save()
    const blob = new Blob([finalBytes], { type: 'application/pdf' })
    const formData = new FormData()
    formData.append('file', blob, props.file.original_filename)

    const res = await fetch(`${API_BASE_URL}/files/${props.file.id}`, {
      method: 'PUT',
      body: formData,
    })

    if (res.ok) {
      message.value = 'Saved'
      emit('saved')
      await loadAndRender()
    } else {
      message.value = 'Save failed'
    }
  } catch (e) {
    message.value = `Error: ${e.message}`
  } finally {
    isSaving.value = false
  }
}

onMounted(loadAndRender)
</script>

<style scoped>
.pdf-editor {
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.file-title {
  font-weight: bold;
  margin-right: 12px;
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

button.active {
  background: #000;
  color: #fff;
}

.pages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.page {
  position: relative;
  border: 1px solid #000;
}

.page canvas {
  position: absolute;
  top: 0;
  left: 0;
}

.overlay {
  cursor: default;
}

.overlay.mode-draw {
  cursor: crosshair;
}

.overlay.mode-text {
  cursor: text;
}

.text-annotation {
  position: absolute;
  min-width: 100px;
  min-height: 20px;
  border: 1px dashed #000;
  background: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  font-family: Helvetica, Arial, sans-serif;
  padding: 2px;
  resize: both;
  overflow: hidden;
}
</style>
