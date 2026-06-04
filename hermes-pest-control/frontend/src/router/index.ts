import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { REQUIRE_LOGIN, getStoredAuthIndicator } from '../services/api'

// Import layouts
import DashboardLayout from '../layouts/DashboardLayout.vue'

// Import pages
import LoginPage from '../pages/LoginPage.vue'
import OperationsDashboardPage from '../pages/OperationsDashboardPage.vue'
import AnalyticsPage from '../pages/AnalyticsPage.vue'
import AiPerformancePage from '../pages/AiPerformancePage.vue'
import AuditPage from '../pages/AuditPage.vue'
import IncidentsPage from '../pages/IncidentsPage.vue'
import IncidentDetailPage from '../pages/IncidentDetailPage.vue'
import VisitsPage from '../pages/VisitsPage.vue'
import VisitDetailPage from '../pages/VisitDetailPage.vue'
import TechniciansPage from '../pages/TechniciansPage.vue'
import TechnicianDetailPage from '../pages/TechnicianDetailPage.vue'
import DocumentsPage from '../pages/DocumentsPage.vue'
import DocumentDetailPage from '../pages/DocumentDetailPage.vue'
import HumanReviewPage from '../pages/HumanReviewPage.vue'
import HumanReviewDetailPage from '../pages/HumanReviewDetailPage.vue'
import ToolExecutionsPage from '../pages/ToolExecutionsPage.vue'
import ToolExecutionDetailPage from '../pages/ToolExecutionDetailPage.vue'
import ShadowDecisionDetailPage from '../pages/ShadowDecisionDetailPage.vue'
import CalendarPage from '../pages/CalendarPage.vue'


const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: LoginPage
  },
  {
    path: '/',
    component: DashboardLayout,
    children: [
      {
        path: '',
        redirect: '/operations'
      },
      {
        path: 'dashboard',
        redirect: '/operations'
      },
      {
        path: 'operations',
        name: 'operations',
        component: OperationsDashboardPage
      },
      {
        path: 'analytics',
        name: 'analytics',
        component: AnalyticsPage
      },
      {
        path: 'ai-performance',
        name: 'ai-performance',
        component: AiPerformancePage
      },
      {
        path: 'audit',
        name: 'audit',
        component: AuditPage
      },
      {
        path: 'incidents',
        name: 'incidents',
        component: IncidentsPage
      },
      {
        path: 'incidents/:id',
        name: 'incident-detail',
        component: IncidentDetailPage,
        props: true
      },
      {
        path: 'visits',
        name: 'visits',
        component: VisitsPage
      },
      {
        path: 'visits/:id',
        name: 'visit-detail',
        component: VisitDetailPage,
        props: true
      },
      {
        path: 'technicians',
        name: 'technicians',
        component: TechniciansPage
      },
      {
        path: 'technicians/:id',
        name: 'technician-detail',
        component: TechnicianDetailPage,
        props: true
      },
      {
        path: 'documents',
        name: 'documents',
        component: DocumentsPage
      },
      {
        path: 'documents/:id',
        name: 'document-detail',
        component: DocumentDetailPage,
        props: true
      },
      {
        path: 'reviews',
        name: 'reviews',
        component: HumanReviewPage
      },
      {
        path: 'reviews/:id',
        name: 'review-detail',
        component: HumanReviewDetailPage,
        props: true
      },
      {
        path: 'tools',
        name: 'tools',
        component: ToolExecutionsPage
      },
      {
        path: 'tools/:id',
        name: 'tool-detail',
        component: ToolExecutionDetailPage,
        props: true
      },
      {
        path: 'audit/shadow-decisions/:id',
        name: 'shadow-decision-detail',
        component: ShadowDecisionDetailPage,
        props: true
      },
      {
        path: 'calendar',
        name: 'calendar',
        component: CalendarPage
      }
    ]
  },
  // Fallback redirect
  {
    path: '/:pathMatch(.*)*',
    redirect: '/operations'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const adminApiKey = getStoredAuthIndicator()
  const hasAccess = !REQUIRE_LOGIN || Boolean(adminApiKey)

  if (REQUIRE_LOGIN && !hasAccess && to.name !== 'login') {
    next({ name: 'login' })
  } else if (REQUIRE_LOGIN && hasAccess && to.name === 'login') {
    next({ name: 'operations' })
  } else {
    next()
  }
})

export default router
