<template>
  <div class="legend">
    <div class="legend-item">
      <span class="legend-color" style="background-color: #ff4d4f;"></span>
      <span>信息缺失</span>
    </div>
    <div class="legend-item">
      <span class="legend-color" style="background-color: #52c41a;"></span>
      <span>结论明确</span>
    </div>
    <div class="legend-item">
      <span class="legend-color" style="background-color: #1890ff;"></span>
      <span>结论待完善</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// 图例组件，无需 props
</script>

<style scoped lang="less">
.legend {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.95);
  padding: 12px 16px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 10;

  .legend-item {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    font-size: 12px;
    color: #666;

    &:last-child {
      margin-bottom: 0;
    }

    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 2px;
      margin-right: 8px;
      border: 1px solid #ddd;
    }
  }
}
</style>

