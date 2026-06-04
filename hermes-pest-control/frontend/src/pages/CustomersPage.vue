<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/dashboard/PageHeader.vue'
import LoadingState from '../components/dashboard/LoadingState.vue'
import EmptyState from '../components/dashboard/EmptyState.vue'
import ErrorBanner from '../components/dashboard/ErrorBanner.vue'
import {
  fetchCustomers,
  createCustomer,
  fetchCustomerSites,
  fetchCustomerContracts,
  type Customer,
  type Site,
  type Contract
} from '../services/api'
import { formatPestType } from '../utils/labels'

const router = useRouter()
const loading = ref(true)
const error = ref<string | null>(null)

// Datos del CRM
const customers = ref<Customer[]>([])
const customerSites = ref<Record<string, Site[]>>({})
const customerContracts = ref<Record<string, Contract[]>>({})

// Filtros y búsquedas
const search = ref('')
const typeFilter = ref('')
const contractStatusFilter = ref('')

// Control del modal de creación
const showCreateModal = ref(false)
const submitting = ref(false)
const newCustomer = ref({
  name: '',
  email: '',
  phone: '',
  customer_type: 'HOSPITALITY'
})

// Cargar todos los clientes y sus sub-recursos en paralelo
async function loadData() {
  loading.value = true
  error.value = null
  try {
    const list = await fetchCustomers()
    customers.value = list

    // Cargar locales y contratos en paralelo para cada cliente
    await Promise.all(
      list.map(async (customer) => {
        try {
          const [sites, contracts] = await Promise.all([
            fetchCustomerSites(customer.id),
            fetchCustomerContracts(customer.id)
          ])
          customerSites.value[customer.id] = sites
          customerContracts.value[customer.id] = contracts
        } catch (err) {
          console.error(`Error cargando detalles para cliente ${customer.id}:`, err)
        }
      })
    )
  } catch (err: any) {
    error.value = err?.message || 'Error al cargar los clientes.'
  } finally {
    loading.value = false
  }
}

// Registrar un cliente nuevo
async function handleCreateCustomer() {
  if (!newCustomer.value.name.trim()) return
  submitting.value = true
  error.value = null
  try {
    const created = await createCustomer({
      name: newCustomer.value.name,
      email: newCustomer.value.email,
      phone: newCustomer.value.phone,
      customer_type: newCustomer.value.customer_type
    })

    // Inicializar registros en local
    customerSites.value[created.id] = []
    customerContracts.value[created.id] = []

    // Recargar o empujar a la lista
    customers.value.unshift(created)

    // Resetear formulario y cerrar modal
    newCustomer.value = {
      name: '',
      email: '',
      phone: '',
      customer_type: 'HOSPITALITY'
    }
    showCreateModal.value = false

    // Navegar al workspace del nuevo cliente para configurarlo
    void router.push(`/customers/${created.id}`)
  } catch (err: any) {
    error.value = err?.message || 'No se pudo registrar el cliente.'
  } finally {
    submitting.value = false
  }
}

// Navegar al Workspace 360 del Cliente
function openCustomerWorkspace(id: string) {
  void router.push(`/customers/${encodeURIComponent(id)}`)
}

// KPIs calculados
const totalCustomersCount = computed(() => customers.value.length)

const totalSitesCount = computed(() => {
  return Object.values(customerSites.value).reduce((acc, list) => acc + list.length, 0)
})

const activeContractsCount = computed(() => {
  return Object.values(customerContracts.value)
    .flatMap(list => list)
    .filter(c => c.status === 'active').length
})

const monthlyRecurringRevenue = computed(() => {
  return Object.values(customerContracts.value)
    .flatMap(list => list)
    .filter(c => c.status === 'active')
    .reduce((acc, c) => acc + c.amount, 0)
})

// Filtrar clientes
const filteredCustomers = computed(() => {
  return customers.value.filter((c) => {
    const matchesSearch = c.name.toLowerCase().includes(search.value.toLowerCase()) ||
      c.email.toLowerCase().includes(search.value.toLowerCase()) ||
      c.phone.includes(search.value)

    const matchesType = !typeFilter.value || c.customer_type === typeFilter.value

    const contracts = customerContracts.value[c.id] || []
    const hasActiveContract = contracts.some(con => con.status === 'active')

    let matchesContract = true
    if (contractStatusFilter.value === 'active') {
      matchesContract = hasActiveContract
    } else if (contractStatusFilter.value === 'none') {
      matchesContract = !hasActiveContract
    }

    return matchesSearch && matchesType && matchesContract
  })
})

function translateCustomerType(type: string): string {
  const mapping: Record<string, string> = {
    HOSPITALITY: 'Hostelería / Restauración',
    FOOD_BUSINESS: 'Industria Alimentaria',
    COMMUNITY: 'Comunidad de Vecinos',
    PRIVATE_HOME: 'Particular / Hogar',
    INDUSTRIAL: 'Polígono / Industrial',
    UNKNOWN: 'No clasificado'
  }
  return mapping[type] || type
}

function getCustomerTypeClass(type: string): string {
  const mapping: Record<string, string> = {
    HOSPITALITY: 'badge-hospitality',
    FOOD_BUSINESS: 'badge-food',
    COMMUNITY: 'badge-community',
    PRIVATE_HOME: 'badge-home',
    INDUSTRIAL: 'badge-industrial',
    UNKNOWN: 'badge-unknown'
  }
  return mapping[type] || ''
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="customers-page">
    <div class="header-container">
      <PageHeader
        title="Gestión de Clientes (CRM)"
        subtitle="Consola unificada para administración de cuentas, locales geolocalizados y planes preventivos contratados."
      />
      <button class="primaryButton" type="button" @click="showCreateModal = true">
        Registrar Cliente
      </button>
    </div>

    <!-- KPIs del Dominio de Clientes -->
    <section class="dashboardLayout" aria-label="Indicadores clave de clientes">
      <div class="metricCard">
        <span class="metricTitle">Clientes Registrados</span>
        <span class="metricValue">{{ totalCustomersCount }}</span>
      </div>
      <div class="metricCard">
        <span class="metricTitle">Locales / Puntos de Control</span>
        <span class="metricValue text-cyan">{{ totalSitesCount }}</span>
      </div>
      <div class="metricCard">
        <span class="metricTitle">Contratos Preventivos Activos</span>
        <span class="metricValue text-emerald">{{ activeContractsCount }}</span>
      </div>
      <div class="metricCard">
        <span class="metricTitle">Ingresos Recurrentes (MRR)</span>
        <span class="metricValue text-amber">{{ monthlyRecurringRevenue.toFixed(2) }}€</span>
      </div>
    </section>

    <!-- Filtros de Búsqueda -->
    <section class="filters" aria-label="Filtros de búsqueda de clientes">
      <label>
        Buscar Cliente
        <input
          v-model="search"
          type="text"
          placeholder="Nombre, email o teléfono..."
        />
      </label>

      <label>
        Tipo de Local
        <select v-model="typeFilter">
          <option value="">Todos los tipos</option>
          <option value="HOSPITALITY">Hostelería / Restauración</option>
          <option value="FOOD_BUSINESS">Industria Alimentaria</option>
          <option value="COMMUNITY">Comunidad de Vecinos</option>
          <option value="PRIVATE_HOME">Particular / Hogar</option>
          <option value="INDUSTRIAL">Polígono / Industrial</option>
          <option value="UNKNOWN">No Clasificado</option>
        </select>
      </label>

      <label>
        Estado del Contrato
        <select v-model="contractStatusFilter">
          <option value="">Todos</option>
          <option value="active">Con contrato preventivo</option>
          <option value="none">Sin contrato preventivo</option>
        </select>
      </label>

      <button
        class="secondaryButton"
        type="button"
        :disabled="!search && !typeFilter && !contractStatusFilter"
        @click="search = ''; typeFilter = ''; contractStatusFilter = ''"
      >
        Limpiar
      </button>
    </section>

    <!-- Listado de Clientes con tarjetas Glassmorphism -->
    <section class="contentBand">
      <LoadingState v-if="loading" message="Cargando cartera de clientes..." />
      <ErrorBanner v-else-if="error" :error="error" @dismiss="error = null" />
      <EmptyState v-else-if="filteredCustomers.length === 0" message="No se encontraron clientes que coincidan con los filtros." />

      <div v-else class="customers-grid">
        <div
          v-for="customer in filteredCustomers"
          :key="customer.id"
          class="customer-card"
        >
          <div class="card-header">
            <span class="badge" :class="getCustomerTypeClass(customer.customer_type)">
              {{ translateCustomerType(customer.customer_type) }}
            </span>
            <div class="contract-status">
              <span
                v-if="(customerContracts[customer.id] || []).some(con => con.status === 'active')"
                class="badge contract-active"
              >
                Mantenimiento Activo
              </span>
              <span v-else class="badge contract-inactive">
                Sin Contrato
              </span>
            </div>
          </div>

          <h3 class="customer-name">{{ customer.name }}</h3>

          <div class="customer-contact">
            <div class="contact-item">
              <svg class="contact-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              <span>{{ customer.email || 'Sin correo registrado' }}</span>
            </div>
            <div class="contact-item">
              <svg class="contact-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-2.824-1.502-5.187-3.865-6.689-6.69l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              <span>{{ customer.phone || 'Sin teléfono registrado' }}</span>
            </div>
          </div>

          <div class="card-details">
            <div class="detail-metric">
              <span class="detail-label">Locales</span>
              <span class="detail-value">{{ (customerSites[customer.id] || []).length }}</span>
            </div>
            <div class="detail-metric">
              <span class="detail-label">Facturación</span>
              <span class="detail-value text-emerald">
                {{ (customerContracts[customer.id] || [])
                  .filter(con => con.status === 'active')
                  .reduce((acc, con) => acc + con.amount, 0).toFixed(2) }}€/mes
              </span>
            </div>
          </div>

          <button
            class="secondaryButton card-action-btn"
            type="button"
            @click="openCustomerWorkspace(customer.id)"
          >
            Workspace 360°
            <svg class="arrow-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </button>
        </div>
      </div>
    </section>

    <!-- Modal para registrar nuevo cliente -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Registrar Nuevo Cliente</h3>
          <button class="close-btn" type="button" @click="showCreateModal = false">&times;</button>
        </div>
        <form @submit.prevent="handleCreateCustomer" class="modal-form">
          <label>
            Nombre Comercial / Razón Social
            <input
              v-model="newCustomer.name"
              type="text"
              placeholder="Ej. Bar Pepe, Pizzería Roma..."
              required
            />
          </label>

          <label>
            Correo Electrónico
            <input
              v-model="newCustomer.email"
              type="email"
              placeholder="cliente@ejemplo.com"
            />
          </label>

          <label>
            Teléfono de Contacto
            <input
              v-model="newCustomer.phone"
              type="tel"
              placeholder="+34 600 000 000"
            />
          </label>

          <label>
            Tipo de Local
            <select v-model="newCustomer.customer_type">
              <option value="HOSPITALITY">Hostelería / Restauración</option>
              <option value="FOOD_BUSINESS">Industria Alimentaria</option>
              <option value="COMMUNITY">Comunidad de Vecinos</option>
              <option value="PRIVATE_HOME">Particular / Hogar</option>
              <option value="INDUSTRIAL">Polígono / Industrial</option>
              <option value="UNKNOWN">No Clasificado</option>
            </select>
          </label>

          <div class="modal-actions">
            <button class="secondaryButton" type="button" @click="showCreateModal = false">
              Cancelar
            </button>
            <button class="primaryButton" type="submit" :disabled="submitting">
              {{ submitting ? 'Guardando...' : 'Crear Cliente' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.customers-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

/* Colores para valores numéricos en KPIs */
.text-cyan { color: #22d3ee; }
.text-emerald { color: #34d399; }
.text-amber { color: #fbbf24; }

/* Grid de clientes */
.customers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  margin-top: 10px;
}

/* Tarjeta Glassmorphism */
.customer-card {
  background: rgba(24, 24, 27, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.3s ease;
}

.customer-card:hover {
  border-color: #3f3f46;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

/* Estilos de Badges para Tipos de Locales */
.badge-hospitality {
  background: rgba(139, 92, 246, 0.15);
  color: #c084fc;
  border: 1px solid rgba(139, 92, 246, 0.2);
}
.badge-food {
  background: rgba(236, 72, 153, 0.15);
  color: #f472b6;
  border: 1px solid rgba(236, 72, 153, 0.2);
}
.badge-community {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}
.badge-home {
  background: rgba(45, 212, 191, 0.15);
  color: #2dd4bf;
  border: 1px solid rgba(45, 212, 191, 0.2);
}
.badge-industrial {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
  border: 1px solid rgba(249, 115, 22, 0.2);
}
.badge-unknown {
  background: rgba(113, 113, 122, 0.15);
  color: #a1a1aa;
  border: 1px solid rgba(113, 113, 122, 0.2);
}

/* Badges de Contrato */
.contract-active {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}
.contract-inactive {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.customer-name {
  font-size: 18px;
  font-weight: 800;
  color: #f4f4f5;
  margin: 0;
}

.customer-contact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: #a1a1aa;
  border-bottom: 1px solid #27272a;
  padding-bottom: 14px;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.contact-icon {
  width: 14px;
  height: 14px;
  color: #71717a;
}

.card-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 10px;
  font-weight: 800;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  font-size: 15px;
  font-weight: 700;
  color: #e4e4e7;
}

.card-action-btn {
  width: 100%;
  margin-top: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.card-action-btn:hover .arrow-icon {
  transform: translateX(4px);
}

.arrow-icon {
  width: 12px;
  height: 12px;
  transition: transform 0.2s ease;
}

/* Modal Styling */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  background: #18181b;
  border: 1px solid #27272a;
  border-radius: 12px;
  padding: 24px;
  width: 100%;
  max-width: 480px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.close-btn {
  background: transparent;
  border: 0;
  color: #a1a1aa;
  font-size: 24px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.close-btn:hover {
  color: #f4f4f5;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-form label {
  gap: 6px;
}

.modal-form input,
.modal-form select {
  width: 100%;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}
</style>
