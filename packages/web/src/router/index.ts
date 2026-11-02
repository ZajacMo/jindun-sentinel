import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

/**
 * One route per workspace page.  The pages are loaded lazily so the initial
 * bundle only carries the shell.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'overview',
    component: () => import('@/pages/OverviewPage.vue'),
    meta: { navKey: 'nav.overview' },
  },
  {
    path: '/countries',
    name: 'countries',
    component: () => import('@/pages/CountriesPage.vue'),
    meta: { navKey: 'nav.countries' },
  },
  {
    path: '/countries/:code',
    name: 'country-detail',
    component: () => import('@/pages/CountryDetailPage.vue'),
    props: true,
    meta: { navKey: 'nav.countries' },
  },
  {
    path: '/spillover',
    name: 'spillover',
    component: () => import('@/pages/SpilloverPage.vue'),
    meta: { navKey: 'nav.spillover' },
  },
  {
    path: '/alerts',
    name: 'alerts',
    component: () => import('@/pages/AlertsPage.vue'),
    meta: { navKey: 'nav.alerts' },
  },
  {
    path: '/data-quality',
    name: 'data-quality',
    component: () => import('@/pages/DataQualityPage.vue'),
    meta: { navKey: 'nav.dataQuality' },
  },
  {
    path: '/methodology',
    name: 'methodology',
    component: () => import('@/pages/MethodologyPage.vue'),
    meta: { navKey: 'nav.methodology' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'overview' },
  },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router
