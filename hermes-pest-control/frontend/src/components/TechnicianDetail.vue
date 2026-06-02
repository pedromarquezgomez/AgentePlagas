<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createTechnician,
  fetchTechnician,
  isUnauthorizedError,
  updateTechnician,
  type Technician,
} from '../services/api'

const props = defineProps<{
  technicianId: string
}>()

const emit = defineEmits<{
  back: []
  created: [technicianId: string]
  unauthorized: []
}>()

const isNew = computed(() => props.technicianId === 'new')
const technician = ref<Technician | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const saveError = ref<string | null>(null)
const saveSuccess = ref(false)
const formName = ref('')
const formPhone = ref('')
const formEmail = ref('')
const formActive = ref(true)
const formServiceArea = ref('')
const formSkills = ref('')

function syncForm(nextTechnician: Technician | null): void {
  formName.value = nextTechnician?.name ?? ''
  formPhone.value = nextTechnician?.phone ?? ''
  formEmail.value = nextTechnician?.email ?? ''
  formActive.value = nextTechnician?.active ?? true
  formServiceArea.value = nextTechnician?.service_area ?? ''
  formSkills.value = nextTechnician?.skills.join(', ') ?? ''
}

function parseSkills(value: string): string[] {
  return value
    .split(',')
    .map((skill) => skill.trim())
    .filter(Boolean)
}

async function loadTechnician(): Promise<void> {
  error.value = null
  saveError.value = null
  saveSuccess.value = false

  if (isNew.value) {
    technician.value = null
    syncForm(null)
    return
  }

  loading.value = true
  try {
    const loadedTechnician = await fetchTechnician(props.technicianId)
    technician.value = loadedTechnician
    syncForm(loadedTechnician)
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    error.value = err instanceof Error ? err.message : 'No se pudo cargar el técnico'
    technician.value = null
  } finally {
    loading.value = false
  }
}

async function saveTechnician(): Promise<void> {
  saving.value = true
  saveError.value = null
  saveSuccess.value = false

  const payload = {
    name: formName.value.trim(),
    phone: formPhone.value.trim() || null,
    email: formEmail.value.trim() || null,
    active: formActive.value,
    service_area: formServiceArea.value.trim() || null,
    skills: parseSkills(formSkills.value),
  }

  try {
    if (isNew.value) {
      const createdTechnician = await createTechnician(payload)
      technician.value = createdTechnician
      syncForm(createdTechnician)
      saveSuccess.value = true
      emit('created', createdTechnician.id)
      return
    }

    await updateTechnician(props.technicianId, payload)
    const refreshedTechnician = await fetchTechnician(props.technicianId)
    technician.value = refreshedTechnician
    syncForm(refreshedTechnician)
    saveSuccess.value = true
  } catch (err) {
    if (isUnauthorizedError(err)) {
      emit('unauthorized')
      return
    }
    saveError.value = err instanceof Error ? err.message : 'No se pudo guardar el técnico'
  } finally {
    saving.value = false
  }
}

watch(
  () => props.technicianId,
  () => {
    void loadTechnician()
  },
  { immediate: true },
)
</script>

<template>
  <section class="detailShell">
    <div class="detailHeader">
      <button class="secondaryButton" type="button" @click="emit('back')">Volver</button>
      <div>
        <p class="eyebrow">{{ isNew ? 'Nuevo técnico' : 'Detalle de técnico' }}</p>
        <h2>{{ formName || 'Técnico' }}</h2>
      </div>
    </div>

    <div v-if="loading" class="stateMessage">Cargando técnico...</div>
    <div v-else-if="error" class="stateMessage errorMessage">{{ error }}</div>

    <form v-else class="editPanel widePanel" aria-label="Guardar técnico" @submit.prevent="saveTechnician">
      <label>
        Nombre
        <input v-model="formName" :disabled="saving" required type="text" />
      </label>

      <label>
        Teléfono
        <input v-model="formPhone" :disabled="saving" type="tel" />
      </label>

      <label>Correo electrónico<input v-model="formEmail" :disabled="saving" type="email" />
      </label>

      <label>
        Zona de servicio
        <input v-model="formServiceArea" :disabled="saving" type="text" />
      </label>

      <label>
        Especialidades
        <input
          v-model="formSkills"
          :disabled="saving"
          placeholder="cucarachas, roedores"
          type="text"
        />
      </label>

      <label class="checkboxLabel">
        <input v-model="formActive" :disabled="saving" type="checkbox" />
        Activo
      </label>

      <div class="formActions">
        <button class="primaryButton" type="submit" :disabled="saving || !formName.trim()">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
        <span v-if="saveSuccess" class="saveMessage">Guardado correctamente.</span>
      </div>

      <div v-if="saveError" class="stateMessage errorMessage">{{ saveError }}</div>
    </form>
  </section>
</template>
