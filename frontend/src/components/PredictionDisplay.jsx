import React from 'react';
import './PredictionDisplay.css';

function PredictionDisplay({ prediction }) {
  if (!prediction || !prediction.signal) {
    return null;
  }

  let displayClass = '';
  if (prediction.signal.includes('看涨')) {
    displayClass = 'prediction-buy';
  } else if (prediction.signal.includes('看跌')) {
    displayClass = 'prediction-sell';
  } else {
    displayClass = 'prediction-hold';
  }

  return (
    <div className={`prediction-panel ${displayClass}`}>
      {/* 在标题中显示预测日期 */}
      <h2>{prediction.date} 预测</h2>
      <div className="prediction-content">
        <div className="prediction-item">
          <span>方向预测</span>
          <p>{prediction.signal}</p>
        </div>
        <div className="prediction-item">
          <span>价格预测</span>
          <p>￥{prediction.predicted_price}</p>
        </div>
      </div>
    </div>
  );
}

export default PredictionDisplay;
