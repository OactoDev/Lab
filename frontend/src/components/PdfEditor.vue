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

      <span v-if="mode === 'draw' || mode === 'text'" class="swatches">
        <button
          v-for="c in COLORS"
          :key="c"
          class="swatch"
          :class="{ active: color === c }"
          :style="{ background: c }"
          :title="c"
          @click="color = c"
        ></button>
      </span>

      <span v-if="mode === 'draw'" class="sub-controls">
        <button
          v-for="w in STROKE_WIDTHS"
          :key="w.value"
          :class="{ active: strokeWidth === w.value }"
          @click="strokeWidth = w.value"
        >
          {{ w.label }}
        </button>
      </span>

      <span v-if="mode === 'text'" class="sub-controls">
        <button
          v-for="s in FONT_SIZES"
          :key="s.value"
          :class="{ active: fontSize === s.value }"
          @click="fontSize = s.value"
        >
          {{ s.label }}
        </button>
      </span>

      <button @click="undo" :disabled="!canUndo">Undo</button>
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
        <div
          v-for="ann in textAnnotations.filter((a) => a.pageIndex === i)"
          :key="ann.id"
          class="text-annotation-wrap"
          :style="{ left: ann.x + 'px', top: ann.y + 'px' }"
        >
          <button class="annotation-delete" title="Delete" @click="removeAnnotation(ann.id)">×</button>
          <textarea
            v-model="ann.text"
            class="text-annotation"
            :style="{ color: ann.color, fontSize: ann.fontSize + 'px' }"
            :ref="(el) => el && ann.id === lastAnnotationId && el.focus()"
            @blur="onAnnotationBlur(ann)"
          ></textarea>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf'
import pdfjsWorker from 'pdfjs-dist/legacy/build/pdf.worker?url'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'
import { apiFetch } from '../api'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker

const SCALE = 1.3
const COLORS = ['#000000', '#e11d48', '#2563eb', '#16a34a']
const STROKE_WIDTHS = [
  { label: 'Thin', value: 1.5 },
  { label: 'Medium', value: 3 },
  { label: 'Thick', value: 6 },
]
const FONT_SIZES = [
  { label: 'S', value: 12 },
  { label: 'M', value: 16 },
  { label: 'L', value: 22 },
]
const MAX_UNDO_PER_PAGE = 20

const props = defineProps({
  file: { type: Object, required: true },
})

const emit = defineEmits(['close', 'saved'])

const isLoading = ref(true)
const isSaving = ref(false)
const message = ref('')
const mode = ref('none')
const color = ref(COLORS[0])
const strokeWidth = ref(STROKE_WIDTHS[0].value)
const fontSize = ref(FONT_SIZES[0].value)

const numPages = ref(0)
const pageIndices = computed(() => Array.from({ length: numPages.value }, (_, i) => i))
const pageSizes = reactive([])
const renderCanvases = reactive([])
const overlayCanvases = reactive([])
const textAnnotations = ref([])
const lastAnnotationId = ref(null)

const lastDrawnPage = ref(null)
const undoVersion = ref(0)
const canUndo = computed(() => {
  undoVersion.value
  return lastDrawnPage.value !== null && (undoStacks[lastDrawnPage.value]?.length || 0) > 0
})

let drawing = false
let nextAnnotationId = 1
let undoStacks = []

const fetchPdfBytes = async () => {
  const res = await apiFetch(`/download/${props.file.id}`)
  return await res.arrayBuffer()
}

const loadAndRender = async () => {
  isLoading.value = true
  message.value = ''
  textAnnotations.value = []
  undoStacks = []
  lastDrawnPage.value = null

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
    undoStacks[i] = []
  }

  isLoading.value = false
}

const pushUndoSnapshot = (i) => {
  const overlay = overlayCanvases[i]
  if (!overlay) return
  if (!undoStacks[i]) undoStacks[i] = []
  const ctx = overlay.getContext('2d')
  undoStacks[i].push(ctx.getImageData(0, 0, overlay.width, overlay.height))
  if (undoStacks[i].length > MAX_UNDO_PER_PAGE) undoStacks[i].shift()
  lastDrawnPage.value = i
  undoVersion.value++
}

const undo = () => {
  const i = lastDrawnPage.value
  if (i === null || !undoStacks[i] || undoStacks[i].length === 0) return
  const snapshot = undoStacks[i].pop()
  const overlay = overlayCanvases[i]
  overlay.getContext('2d').putImageData(snapshot, 0, 0)
  undoVersion.value++
}

const onPointerDown = (i, event) => {
  if (mode.value !== 'draw') return
  pushUndoSnapshot(i)
  drawing = true
  const ctx = overlayCanvases[i].getContext('2d')
  ctx.strokeStyle = color.value
  ctx.lineWidth = strokeWidth.value
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
    color: color.value,
    fontSize: fontSize.value,
  })
  lastAnnotationId.value = id
}

const removeAnnotation = (id) => {
  textAnnotations.value = textAnnotations.value.filter((a) => a.id !== id)
}

const onAnnotationBlur = (ann) => {
  if (!ann.text.trim()) {
    removeAnnotation(ann.id)
  }
}

const clearPage = () => {
  pageIndices.value.forEach((i) => {
    const overlay = overlayCanvases[i]
    if (overlay) {
      overlay.getContext('2d').clearRect(0, 0, overlay.width, overlay.height)
      undoStacks[i] = []
    }
  })
  textAnnotations.value = []
  lastDrawnPage.value = null
  undoVersion.value++
}

const hexToRgb01 = (hex) => {
  const n = parseInt(hex.slice(1), 16)
  return rgb(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255)
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
        const pdfX = ann.x / SCALE
        const pdfY = ph - ann.y / SCALE - ann.fontSize * 0.8
        pdfPage.drawText(ann.text, {
          x: pdfX,
          y: pdfY,
          size: ann.fontSize,
          font,
          color: hexToRgb01(ann.color),
        })
      }
    }

    const finalBytes = await pdfLibDoc.save()
    const blob = new Blob([finalBytes], { type: 'application/pdf' })
    const formData = new FormData()
    formData.append('file', blob, props.file.original_filename)

    const res = await apiFetch(`/files/${props.file.id}`, {
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

button:disabled {
  opacity: 0.4;
  cursor: default;
}

.swatches,
.sub-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  padding-left: 4px;
  border-left: 1px solid #000;
}

.sub-controls button {
  padding: 6px 8px;
  font-size: 12px;
}

.swatch {
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid #000;
}

.swatch.active {
  outline: 2px solid #000;
  outline-offset: 2px;
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

.text-annotation-wrap {
  position: absolute;
}

.annotation-delete {
  position: absolute;
  top: -10px;
  right: -10px;
  width: 18px;
  height: 18px;
  padding: 0;
  line-height: 1;
  font-size: 12px;
  border: 1px solid #000;
  background: #fff;
  color: #000;
  cursor: pointer;
  z-index: 1;
}

.text-annotation {
  position: relative;
  min-width: 100px;
  min-height: 20px;
  border: 1px dashed #000;
  background: rgba(255, 255, 255, 0.85);
  font-family: Helvetica, Arial, sans-serif;
  padding: 2px;
  resize: both;
  overflow: hidden;
}
</style>
