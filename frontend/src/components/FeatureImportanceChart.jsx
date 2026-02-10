import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import './FeatureImportanceChart.css';

function FeatureImportanceChart({ featureImportance }) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (chartRef.current && featureImportance && featureImportance.length > 0) {
      const myChart = echarts.init(chartRef.current, 'dark');

      // 数据需要反转，因为ECharts的条形图默认第一个数据显示在最下面
      const reversedData = [...featureImportance].reverse();
      const features = reversedData.map(item => item[0]);
      const importances = reversedData.map(item => item[1]);

      const option = {
        title: {
          text: '特征重要度分析',
          left: 'center',
          textStyle: {
            color: '#e0e0e0'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'value',
          boundaryGap: [0, 0.01]
        },
        yAxis: {
          type: 'category',
          data: features,
          axisLabel: {
            interval: 0, // 强制显示所有标签
            rotate: 0 // 如果标签太长可以考虑旋转
          }
        },
        series: [
          {
            name: '重要度',
            type: 'bar',
            data: importances,
            itemStyle: {
                color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                    { offset: 0, color: '#0d6efd' },
                    { offset: 1, color: '#198754' }
                ])
            }
          }
        ]
      };

      myChart.setOption(option);

      return () => {
        myChart.dispose();
      };
    }
  }, [featureImportance]);

  if (!featureImportance || featureImportance.length === 0) {
    return null;
  }

  return <div ref={chartRef} className="chart-container" style={{ marginTop: '30px' }}></div>;
}

export default FeatureImportanceChart;
