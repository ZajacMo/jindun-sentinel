import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import type { Plugin } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { localeCataloguePlugin } from './vite-plugin-locale-catalogue.ts'

// The shared locale catalogue lives at <repo-root>/locales, which is
// "../../locales" relative to this package.  The plugin reads it at build time
// so the front end and the Python server always render the very same strings.
const localeDir = fileURLToPath(new URL('../../locales', import.meta.url))

export default defineConfig({
  /**
   * `vitest@3` depends on Vite 7 while this package runs Vite 8, so the two
   * major versions ship incompatible `Plugin` types.  The plugin list is the
   * only place where the two type universes meet, so the bridge is made here
   * explicitly; every other type in the project is checked normally.
   */
  plugins: [vue(), localeCataloguePlugin({ dir: localeDir })] as unknown as Plugin[],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // The locale catalogue and the methodology documents live outside this
    // package, so the dev server has to be allowed to serve them.
    fs: {
      allow: [
        fileURLToPath(new URL('.', import.meta.url)),
        fileURLToPath(new URL('../..', import.meta.url)),
      ],
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        // Rolldown (Vite 8) only accepts the function form of `manualChunks`.
        manualChunks(id: string): string | undefined {
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'echarts'
          }
          if (
            id.includes('node_modules/element-plus') ||
            id.includes('node_modules/@element-plus')
          ) {
            return 'element-plus'
          }
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/**/*.spec.ts'],
    restoreMocks: true,
  },
})
