<template>
  <div class="page">
    <div class="toolbar">
      <span style="margin-right:8px">统计维度：</span>
      <a-space>
        <a-button :type="days===30?'primary':'default'" @click="setDays(30)">30天</a-button>
        <a-button :type="days===90?'primary':'default'" @click="setDays(90)">90天</a-button>
        <a-button :type="days===180?'primary':'default'" @click="setDays(180)">180天</a-button>
        <span>或自定义：</span>
        <a-input-number v-model:value="days" :min="1" :max="100000" @change="onDaysChange" />
        <a-button type="primary" @click="fetchTags">刷新</a-button>
      </a-space>
      <span style="margin-left:16px">记录数：{{ totalHits }}</span>
    </div>
    <div class="tags">
      <a-tag
        v-for="t in tags"
        :key="t.rule_name"
        color="blue"
        @click="onSelectRule(t.rule_name)"
        style="cursor:pointer;margin-bottom:8px"
      >{{ t.rule_name }} ({{ t.hit_count }})</a-tag>
    </div>
    <div class="content">
      <div class="table">
        <a-table
          :columns="columns"
          :data-source="stocks"
          :loading="loading"
          row-key="code"
          :pagination="{ pageSize: 20 }"
        />
      </div>
      <div class="chart">
        <div ref="chartEl" style="height:360px"></div>
      </div>
    </div>
  </div>
  
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getRuleTags, getRuleHitStocks } from '@/api/stocks'

type RuleTag = { rule_name: string; hit_count: number }
type RuleHitStock = { code: string; hit_count: number }

const days = ref<number>(3000)
const tags = ref<RuleTag[]>([])
const totalHits = ref<number>(0)
const selectedRule = ref<string>('')
const stocks = ref<RuleHitStock[]>([])
const loading = ref(false)
const chartEl = ref<HTMLDivElement | null>(null)

const columns = [
  { title: '股票', dataIndex: 'code' },
  { title: '命中次数', dataIndex: 'hit_count' },
]

const fetchTags = async () => {
  const data = await getRuleTags(days.value)
  tags.value = data
  totalHits.value = Array.isArray(data) ? data.reduce((s, i:any) => s + (i.hit_count || 0), 0) : 0
}

const fetchStocks = async () => {
  if (!selectedRule.value) return
  loading.value = true
  const data = await getRuleHitStocks(selectedRule.value, days.value)
  stocks.value = data
  loading.value = false
  renderChart()
}

const onSelectRule = (name: string) => {
  selectedRule.value = name
  fetchStocks()
}

const renderChart = () => {
  if (!chartEl.value) return
  const inst = echarts.init(chartEl.value)
  const top = stocks.value.slice(0, 20)
  inst.setOption({
    tooltip: {},
    xAxis: { type: 'category', data: top.map(i => i.code) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: top.map(i => i.hit_count) }]
  })
}

onMounted(async () => {
  await fetchTags()
})

const onDaysChange = () => {
  fetchTags()
  if (selectedRule.value) fetchStocks()
}

const setDays = (n: number) => {
  days.value = n
  onDaysChange()
}
</script>

<style scoped>
.page { padding: 16px; }
.toolbar { margin-bottom: 12px; }
.tags { margin-bottom: 12px; }
.content { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
</style>


