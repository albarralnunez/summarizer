import React from 'react'
import { SummaryResultType } from '../types'

interface SummaryResultProps {
  result: SummaryResultType | null;
  responseTime: number | null;
}

export const SummaryResult: React.FC<SummaryResultProps> = ({ result, responseTime }): JSX.Element | null => {
  if (!result) return null

  return (
    <div className="result">
      <h2>Summary</h2>
      <div className="result-info">
        {responseTime !== null && (
          <p><strong>Total response time:</strong> {responseTime.toFixed(3)} seconds</p>
        )}
        {result.backend_processing_time !== null && (
          <p><strong>Backend processing time:</strong> {result.backend_processing_time.toFixed(3)} seconds</p>
        )}
      </div>
      <div className="summary-content">
        {result.summary.map((sentence: string, index: number) => (
          <blockquote key={index} className="summary-sentence">
            {sentence}
          </blockquote>
        ))}
      </div>
    </div>
  )
}
