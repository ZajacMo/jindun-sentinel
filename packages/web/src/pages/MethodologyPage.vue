<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import EstimatorStack from '@/components/diagrams/EstimatorStack.vue'
import { methodologyDocuments, hasMethodologyDocuments } from '@/content/methodology'
import { renderMarkdown } from '@/utils/markdown'
import { METHOD_CODES } from '@/utils/codes'

/**
 * The methodology page.
 *
 * The method documentation of the repository, rendered from the Markdown
 * notes in `docs/methodology/`, together with the diagram of the estimator
 * stack that the notes describe.
 */
const { t } = useI18n()

/** Model names are not translated. */
const MODEL_VAR = 'VAR'
const MODEL_VMA = 'VMA'

const estimators = computed(() =>
  METHOD_CODES.map((code) => ({
    code,
    label: t(`method.${code}`),
    note: code === 'paper_equation' ? t('lens.percentile') : undefined,
  })),
)

const documents = computed(() =>
  methodologyDocuments.map((document) => ({
    ...document,
    html: renderMarkdown(document.source),
  })),
)
</script>

<template>
  <div class="jd-stack">
    <header class="jd-page-header">
      <div>
        <h1>{{ t('nav.methodology') }}</h1>
        <p>{{ t('app.tagline') }}</p>
      </div>
    </header>

    <div class="jd-stack">
      <section class="jd-panel">
        <h2>{{ t('method.paper_equation') }}</h2>
        <EstimatorStack
          :title="t('nav.methodology')"
          :model="MODEL_VAR"
          :vma="MODEL_VMA"
          :decomposition="t('method.paper_equation')"
          :estimators="estimators"
          :convention="t('metric.ownShare')"
          :convention-note="t('common.notes')"
        />
      </section>

      <section class="jd-panel">
        <h2>{{ t('method.paper_equation') }}</h2>
        <div class="jd-grid jd-grid-2">
          <el-descriptions
            v-for="estimator in estimators"
            :key="estimator.code"
            :title="estimator.label"
            :column="1"
            border
          >
            <el-descriptions-item :label="t('metric.bucket')">
              {{ estimator.code }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </section>

      <section
        v-for="document in documents"
        :key="document.id"
        class="jd-panel"
      >
        <h2>{{ document.title ?? document.id }}</h2>
        <div class="jd-markdown" v-html="document.html" />
      </section>

      <section v-if="!hasMethodologyDocuments" class="jd-panel">
        <h2>{{ t('nav.methodology') }}</h2>
        <p class="jd-muted">{{ t('common.empty') }}</p>
      </section>
    </div>
  </div>
</template>
