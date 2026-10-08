<template>
  <a-modal
    v-model:visible="visible"
    :title="id ? '股票详情' : '创建股票'"
    @ok="save"
    :confirmLoading="loading"
    centered
    :width="800"
  >
    <a-tabs v-if="id" default-active-key="basic">
      <a-tab-pane key="basic" tab="基本信息">
        <a-form ref="formRef" :model="form" :rules="rules" :label-col="{ span: 6 }">
          <a-form-item label="代码" name="code">
            <a-input v-model:value="form.code" :disabled="!!id" placeholder="6位代码" />
          </a-form-item>
          <a-form-item label="名称" name="name">
            <a-input v-model:value="form.name" placeholder="请输入名称" />
          </a-form-item>
          <a-form-item label="市场" name="market">
            <a-select v-model:value="form.market" style="width: 160px">
              <a-select-option value="SH">SH</a-select-option>
              <a-select-option value="SZ">SZ</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="状态" name="status">
            <a-input v-model:value="form.status" placeholder="正常/停牌等" />
          </a-form-item>
        </a-form>
      </a-tab-pane>
      <a-tab-pane key="org" tab="组织信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="组织ID">{{ form.org_id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="中文全称">{{ form.org_name_cn || '-' }}</a-descriptions-item>
          <a-descriptions-item label="英文全称">{{ form.org_name_en || '-' }}</a-descriptions-item>
          <a-descriptions-item label="英文简称">{{ form.org_short_name_en || '-' }}</a-descriptions-item>
          <a-descriptions-item label="曾用名" :span="2">{{ form.pre_name_cn || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="business" tab="业务信息">
        <a-descriptions :column="1" bordered size="small">
          <a-descriptions-item label="主营业务">{{ form.main_operation_business || '-' }}</a-descriptions-item>
          <a-descriptions-item label="经营范围">{{ form.operating_scope || '-' }}</a-descriptions-item>
          <a-descriptions-item label="行业代码">{{ form.industry_code || '-' }}</a-descriptions-item>
          <a-descriptions-item label="行业名称">{{ form.industry_name || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="register" tab="注册信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="地区编码">{{ form.district_encode || '-' }}</a-descriptions-item>
          <a-descriptions-item label="省份">{{ form.provincial_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="成立日期">{{ form.established_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="注册资本">{{ form.reg_asset ? form.reg_asset.toLocaleString() : '-' }}</a-descriptions-item>
          <a-descriptions-item label="注册地址（中文）" :span="2">{{ form.reg_address_cn || '-' }}</a-descriptions-item>
          <a-descriptions-item label="注册地址（英文）" :span="2">{{ form.reg_address_en || '-' }}</a-descriptions-item>
          <a-descriptions-item label="办公地址（中文）" :span="2">{{ form.office_address_cn || '-' }}</a-descriptions-item>
          <a-descriptions-item label="办公地址（英文）" :span="2">{{ form.office_address_en || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="contact" tab="联系信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="电话">{{ form.telephone || '-' }}</a-descriptions-item>
          <a-descriptions-item label="邮编">{{ form.postcode || '-' }}</a-descriptions-item>
          <a-descriptions-item label="传真">{{ form.fax || '-' }}</a-descriptions-item>
          <a-descriptions-item label="邮箱">{{ form.email || '-' }}</a-descriptions-item>
          <a-descriptions-item label="网站" :span="2">{{ form.org_website || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="management" tab="管理信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="法定代表人">{{ form.legal_representative || '-' }}</a-descriptions-item>
          <a-descriptions-item label="董事长">{{ form.chairman || '-' }}</a-descriptions-item>
          <a-descriptions-item label="总经理">{{ form.general_manager || '-' }}</a-descriptions-item>
          <a-descriptions-item label="董事会秘书">{{ form.secretary || '-' }}</a-descriptions-item>
          <a-descriptions-item label="高管人数">{{ form.executives_nums || '-' }}</a-descriptions-item>
          <a-descriptions-item label="实际控制人">{{ form.actual_controller || '-' }}</a-descriptions-item>
          <a-descriptions-item label="企业性质" :span="2">{{ form.classi_name || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="listing" tab="上市信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="上市日期">{{ form.listed_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="实际发行量">{{ form.actual_issue_vol ? form.actual_issue_vol.toLocaleString() : '-' }}</a-descriptions-item>
          <a-descriptions-item label="发行价格">{{ form.issue_price || '-' }}</a-descriptions-item>
          <a-descriptions-item label="实际募集净额">{{ form.actual_rc_net_amt ? form.actual_rc_net_amt.toLocaleString() : '-' }}</a-descriptions-item>
          <a-descriptions-item label="发行后市盈率">{{ form.pe_after_issuing || '-' }}</a-descriptions-item>
          <a-descriptions-item label="网上中签率">{{ form.online_success_rate_of_issue || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
      <a-tab-pane key="other" tab="其他信息">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="员工数">{{ form.staff_num ? form.staff_num.toLocaleString() : '-' }}</a-descriptions-item>
          <a-descriptions-item label="货币编码">{{ form.currency_encode || '-' }}</a-descriptions-item>
          <a-descriptions-item label="货币" :span="2">{{ form.currency || '-' }}</a-descriptions-item>
        </a-descriptions>
      </a-tab-pane>
    </a-tabs>
    <a-form v-else ref="formRef" :model="form" :rules="rules" :label-col="{ span: 5 }">
      <a-form-item label="代码" name="code">
        <a-input v-model:value="form.code" :disabled="!!id" placeholder="6位代码" />
      </a-form-item>
      <a-form-item label="名称" name="name">
        <a-input v-model:value="form.name" placeholder="请输入名称" />
      </a-form-item>
      <a-form-item label="市场" name="market">
        <a-select v-model:value="form.market" style="width: 160px">
          <a-select-option value="SH">SH</a-select-option>
          <a-select-option value="SZ">SZ</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="状态" name="status">
        <a-input v-model:value="form.status" placeholder="正常/停牌等" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script>
import { message } from 'ant-design-vue'
import { getStockInfoDetail, createStockInfo, updateStockInfo } from '@/api/stocks'

export default {
  name: 'StockInfoEditModal',
  data() {
    return {
      id: null,
      visible: false,
      loading: false,
      form: {},
      rules: {
        code: [{ required: true, message: '请输入股票代码' }],
        name: [{ required: true, message: '请输入名称' }],
        market: [{ required: false }],
      }
    }
  },
  watch: {
    visible(v) {
      if (v) {
        this.id ? this.getDetail() : (this.form = {})
      } else {
        this.form = {}
      }
    }
  },
  methods: {
    getDetail() {
      this.loading = true
      getStockInfoDetail(this.id)
        .then((data) => {
          this.form = { ...data }
        })
        .finally(() => { this.loading = false })
    },
    save() {
      this.$refs.formRef.validate()
        .then(() => {
          this.loading = true
          // 创建或更新时只提交基础字段
          const basicFields = {
            code: this.form.code,
            name: this.form.name,
            market: this.form.market,
            status: this.form.status
          }
          return this.id ? updateStockInfo(this.id, basicFields) : createStockInfo(basicFields)
        })
        .then(() => {
          message.success(this.id ? '更新已提交' : '创建成功')
          this.visible = false
          this.$emit('change')
        })
        .finally(() => { this.loading = false })
    }
  }
}
</script>

<style scoped>
</style>


