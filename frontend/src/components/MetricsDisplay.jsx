import React from 'react';
import './MetricsDisplay.css'; // 确保导入CSS文件

function MetricsDisplay({ metrics }) {
  if (!metrics) {
    return <div className="metrics-panel">暂无回测指标</div>;
  }

  return (
    <div className="metrics-panel">
      <h2>回测性能指标</h2>
      <table>
        <tbody>
          {Object.entries(metrics).map(([key, value]) => (
            <tr key={key}>
              <td>{key}:</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default MetricsDisplay;
