import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import './KlineChart.css';

function KlineChart({ klineData, buySignals, sellSignals, isLoading, error }) {
  const chartRef = useRef(null);

  useEffect(() => {
    // 只有在有数据且图表ref存在时才初始化ECharts
    if (chartRef.current && klineData && klineData.length > 0) {
      const myChart = echarts.init(chartRef.current, 'dark');

      const dates = klineData.map(item => item[0]);
      const ohlc = klineData.map(item => item.slice(1)); // [open, close, low, high]

      // 格式化买卖信号数据，使其能在K线上显示标记
      const buyMarkers = buySignals ? buySignals.map(signal => ({
        name: 'Buy',
        value: signal[1],
        xAxis: signal[0],
        yAxis: signal[1],
        itemStyle: { color: '#ef232a' } // 红色向上箭头
      })) : [];

      const sellMarkers = sellSignals ? sellSignals.map(signal => ({
        name: 'Sell',
        value: signal[1],
        xAxis: signal[0],
        yAxis: signal[1],
        itemStyle: { color: '#14b143' } // 绿色向下箭头
      })) : [];

      const option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        grid: {
          left: '10%',
          right: '10%',
          bottom: '15%'
        },
        xAxis: {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          splitNumber: 20,
          min: 'dataMin',
          max: 'dataMax'
        },
        yAxis: {
          scale: true,
          splitArea: {
            show: true
          }
        },
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0],
            start: 80,
            end: 100
          },
          {
            show: true,
            xAxisIndex: [0],
            type: 'slider',
            bottom: '5%',
            start: 80,
            end: 100
          }
        ],
        series: [
          {
            name: '日K',
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
              color: '#ef232a',
              color0: '#14b143',
              borderColor: '#ef232a',
              borderColor0: '#14b143'
            },
            markPoint: {
                data: [
                    ...buyMarkers.map(m => ({ ...m, symbol: 'triangle', symbolSize: 10, symbolOffset: [0, -5] })),
                    ...sellMarkers.map(m => ({ ...m, symbol: 'triangle', symbolRotate: 180, symbolSize: 10, symbolOffset: [0, 5] }))
                ]
            }
          }
        ]
      };

      myChart.setOption(option);

      return () => {
        myChart.dispose();
      };
    } else if (chartRef.current) {
      // 如果没有数据，确保销毁旧的图表实例，防止内存泄漏
      const existingChart = echarts.getInstanceByDom(chartRef.current);
      if (existingChart) {
        existingChart.dispose();
      }
    }
  }, [klineData, buySignals, sellSignals, isLoading, error]);

  return (
    <div className="chart-container">
      {isLoading && <div className="chart-message">正在加载图表数据...</div>}
      {error && <div className="chart-message error-message">加载图表错误: {error}</div>}
      {!isLoading && !error && (!klineData || klineData.length === 0) && (
        <div className="chart-message">暂无图表数据。</div>
      )}
      {/* ECharts将在这里渲染 */}
      <div ref={chartRef} style={{ width: '100%', height: '100%' }}></div>
    </div>
  );
}

export default KlineChart;