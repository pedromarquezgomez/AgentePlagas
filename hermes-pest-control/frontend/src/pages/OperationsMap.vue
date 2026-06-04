<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchIncidents,
  fetchTechnicians,
  fetchVisits,
  type Incident,
  type Technician,
  type Visit
} from '../services/api'
import { formatPestType, formatStatus } from '../utils/labels'
import PageHeader from '../components/dashboard/PageHeader.vue'

const router = useRouter()

const incidents = ref<Incident[]>([])
const technicians = ref<Technician[]>([])
const visits = ref<Visit[]>([])
const loading = ref(true)
const mapError = ref<string | null>(null)

// Leaflet refs
const leafletLoaded = ref(false)
let mapInstance: any = null

// Simulación de Coordenadas de la Costa del Sol
function getCoordinates(locationName: string | null | undefined): [number, number] {
  if (!locationName) return [36.7213, -4.4214] // Málaga Centro
  const loc = locationName.toLowerCase()
  if (loc.includes('torremolinos')) return [36.6203, -4.4994]
  if (loc.includes('benalmádena') || loc.includes('benalmadena')) return [36.5956, -4.5165]
  if (loc.includes('fuengirola')) return [36.5417, -4.6250]
  if (loc.includes('marbella')) return [36.5101, -4.8824]
  if (loc.includes('mijas')) return [36.5958, -4.6373]
  if (loc.includes('rincón') || loc.includes('rincon')) return [36.7164, -4.2783]
  if (loc.includes('antequera')) return [37.0194, -4.5611]
  // Coordenadas aleatorias controladas alrededor de Málaga para evitar superposiciones
  const seed = locationName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const latOffset = ((seed % 100) / 1000) - 0.05
  const lngOffset = (((seed * 7) % 100) / 1000) - 0.05
  return [36.7213 + latOffset, -4.4214 + lngOffset]
}

// Cargar Datos
async function loadData() {
  try {
    const [incList, techList, visitList] = await Promise.all([
      fetchIncidents({ limit: 100 }),
      fetchTechnicians({ limit: 100 }),
      fetchVisits({ limit: 100 })
    ])
    incidents.value = incList
    technicians.value = techList
    visits.value = visitList
  } catch (err) {
    console.error('Error cargando datos para el mapa:', err)
    mapError.value = 'No se pudieron cargar los datos operativos para el mapa.'
  } finally {
    loading.value = false
  }
}

// Inicializar el mapa de Leaflet
function initMap() {
  if (!leafletLoaded.value || loading.value) return
  
  const L = (window as any).L
  if (!L) return

  // Limpiar mapa previo si existe
  if (mapInstance) {
    mapInstance.remove()
  }

  // Crear mapa centrado en la Costa del Sol
  mapInstance = L.map('map-viewport', {
    center: [36.65, -4.52], // Centrado entre Málaga y Fuengirola
    zoom: 11,
    zoomControl: false
  })

  L.control.zoom({ position: 'bottomright' }).addTo(mapInstance)

  // Capa oscura premium
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
  }).addTo(mapInstance)

  // 1. Agregar Incidentes
  incidents.value.forEach(inc => {
    const coords = getCoordinates(inc.location)
    const prio = (inc.priority || '').toLowerCase()
    const isUrgent = prio === 'urgent' || prio === 'high' || prio === 'urgente' || prio === 'alta'
    const isResolved = inc.status === 'completed' || inc.status === 'closed'
    
    let color = '#fbbf24' // Amarillo por defecto
    let shadowColor = 'rgba(251, 191, 36, 0.4)'
    if (isUrgent) {
      color = '#ef4444' // Rojo urgente
      shadowColor = 'rgba(239, 68, 68, 0.4)'
    } else if (isResolved) {
      color = '#10b981' // Verde resuelto
      shadowColor = 'rgba(16, 185, 129, 0.4)'
    }

    // Marcador circular personalizado
    const markerHtml = `
      <div style="
        background: ${color};
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 0 10px ${shadowColor};
      "></div>
    `
    const customIcon = L.divIcon({
      html: markerHtml,
      className: 'custom-leaflet-marker',
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    })

    const popupContent = `
      <div style="font-family: sans-serif; color: #18181b; padding: 4px;">
        <span style="font-size: 10px; font-weight: 800; color: #71717a; text-transform: uppercase;">Incidencia #${inc.id.slice(0, 6).toUpperCase()}</span>
        <h4 style="margin: 4px 0; font-size: 14px; font-weight: 800; color: #1f2937;">${inc.location || 'Localización S/D'}</h4>
        <p style="margin: 0; font-size: 12px; color: #4b5563;">Plaga: <b>${formatPestType(inc.pest_type)}</b></p>
        <p style="margin: 4px 0 0 0; font-size: 11px;">Prioridad: <span style="font-weight: 800; color: ${isUrgent ? '#ef4444' : '#d97706'}">${inc.priority.toUpperCase()}</span> | Estado: <span style="font-weight: 800; color: #374151;">${formatStatus(inc.status)}</span></p>
        <button style="
          margin-top: 8px;
          background: #10b981;
          color: #fff;
          border: 0;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: bold;
          cursor: pointer;
          width: 100%;
        " onclick="window.dispatchEvent(new CustomEvent('map-nav-workspace', { detail: '${inc.id}' }))">
          Abrir en Consola 360°
        </button>
      </div>
    `

    L.marker(coords, { icon: customIcon })
      .addTo(mapInstance)
      .bindPopup(popupContent)
  })

  // 2. Agregar Técnicos
  technicians.value.forEach(tech => {
    const coords = getCoordinates(tech.service_area)
    // Añadimos un pequeño offset a los técnicos para que no se empalmen exactamente con los incidentes
    coords[0] += 0.015
    coords[1] += 0.015

    let color = '#10b981' // Disponible (Verde)
    let dotClass = 'tech-dot-available'
    const statusLabel = tech.active ? 'Disponible' : 'Inactivo'

    const markerHtml = `
      <div class="${dotClass}" style="
        background: #2563eb;
        border: 2px solid #fff;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 10px;
        font-weight: bold;
        box-shadow: 0 0 8px rgba(37, 99, 235, 0.6);
      ">👤</div>
    `
    const customIcon = L.divIcon({
      html: markerHtml,
      className: 'custom-leaflet-tech-marker',
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    })

    const popupContent = `
      <div style="font-family: sans-serif; color: #18181b; padding: 4px;">
        <span style="font-size: 10px; font-weight: 800; color: #71717a; text-transform: uppercase;">Personal de Servicio</span>
        <h4 style="margin: 4px 0; font-size: 14px; font-weight: 800; color: #1f2937;">${tech.name}</h4>
        <p style="margin: 0; font-size: 12px; color: #4b5563;">Zona de Cobertura: <b>📍 ${tech.service_area || 'Costa del Sol'}</b></p>
        <p style="margin: 4px 0 0 0; font-size: 11px;">Estado: <span style="font-weight: 800; color: #10b981;">${statusLabel.toUpperCase()}</span></p>
      </div>
    `

    L.marker(coords, { icon: customIcon })
      .addTo(mapInstance)
      .bindPopup(popupContent)
  })
}

// Inyección dinámica de Leaflet
onMounted(() => {
  void loadData().then(() => {
    if ((window as any).L) {
      leafletLoaded.value = true
      initMap()
      return
    }
    
    // Inyectar CSS
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)

    // Inyectar Script
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => {
      leafletLoaded.value = true
      initMap()
    }
    document.head.appendChild(script)
  })

  // Listener para navegar del mapa a la ficha 360
  window.addEventListener('map-nav-workspace', (e: any) => {
    const incId = e.detail
    if (incId) {
      void router.push(`/incidents/${incId}`)
    }
  })
})
</script>

<template>
  <div class="operations-map-page">
    <div class="sectionHeader">
      <PageHeader
        title="Mapa Operativo Geográfico"
        subtitle="Geolocalización en tiempo real de incidencias activas, visitas técnicas y personal de servicio en la Costa del Sol."
      />
    </div>

    <div v-if="loading" class="map-loading">
      Cargando mapa y sincronizando coordenadas geográficas...
    </div>
    
    <div v-else-if="mapError" class="map-error">
      {{ mapError }}
    </div>

    <div v-else class="map-workspace">
      <!-- Mapa Real Leaflet -->
      <div id="map-viewport" class="map-viewport"></div>

      <!-- Leyenda lateral flotante -->
      <div class="map-legend">
        <h4>Leyenda Operativa</h4>
        
        <div class="legend-section">
          <h5>Incidencias & Servicios</h5>
          <div class="legend-row">
            <span class="legend-circle urgent"></span>
            <span>🔴 Urgente (SLA Crítico)</span>
          </div>
          <div class="legend-row">
            <span class="legend-circle active"></span>
            <span>🟡 Activo (Esta Semana)</span>
          </div>
          <div class="legend-row">
            <span class="legend-circle completed"></span>
            <span>🟢 Completado / Resuelto</span>
          </div>
        </div>

        <div class="legend-section border-top">
          <h5>Personal de Campo</h5>
          <div class="legend-row">
            <span class="legend-square tech">👤</span>
            <span>Técnico Asignado en Ruta</span>
          </div>
        </div>

        <div class="legend-section border-top">
          <h5>Zona de Operaciones</h5>
          <p class="legend-text">Región de Cobertura: Costa del Sol Occidental (Málaga, Torremolinos, Benalmádena, Fuengirola, Marbella).</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.operations-map-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: calc(100vh - 120px);
}

.map-loading,
.map-error {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 8px;
  color: #a1a1aa;
  padding: 80px;
  text-align: center;
  font-weight: 700;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.map-error {
  color: #f87171;
}

.map-workspace {
  position: relative;
  flex-grow: 1;
  border: 1px solid #27272a;
  border-radius: 8px;
  overflow: hidden;
  height: 100%;
}

.map-viewport {
  width: 100%;
  height: 100%;
  background: #09090b;
  z-index: 1;
}

/* Leyenda flotante */
.map-legend {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(9, 9, 11, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid #27272a;
  border-radius: 8px;
  padding: 16px;
  width: 260px;
  z-index: 50;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.map-legend h4 {
  font-size: 12px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.legend-section h5 {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  margin: 0 0 8px 0;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: #d4d4d8;
  font-weight: 600;
  margin-bottom: 6px;
}

.legend-circle {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  border: 1.5px solid #fff;
}

.legend-circle.urgent { background: #ef4444; }
.legend-circle.active { background: #fbbf24; }
.legend-circle.completed { background: #10b981; }

.legend-square.tech {
  width: 18px;
  height: 18px;
  background: #2563eb;
  border: 1px solid #fff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
}

.border-top {
  border-top: 1px solid #27272a;
  padding-top: 10px;
}

.legend-text {
  font-size: 10px;
  color: #71717a;
  margin: 0;
  line-height: 1.4;
  font-style: italic;
}
</style>
