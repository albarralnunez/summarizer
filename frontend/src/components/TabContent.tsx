import React from 'react';
import { ProcessingMetadata } from './ProcessingMetadata';
import { ProfilingData } from './ProfilingData';

interface TabContentProps {
  activeTab: 'summary' | 'profiling';
  summary: string[];
  method: string;
  processor: string;
  backend_processing_time: number;
  responseTime: number;
  profiling_data?: {
    functions: Array<{
      function_name: string;
      total_time: number;
      total_exec_time: number;
      percentage: number;
      calls: number;
      memory_per_call: number;
    }>;
    memory_usage: number;
    memory_peak: number;
    memory_details: Array<{
      file: string;
      line: number;
      size: number;
      count: number;
    }>;
  };
}

export const TabContent: React.FC<TabContentProps> = ({
  activeTab,
  summary,
  method,
  processor,
  backend_processing_time,
  responseTime,
  profiling_data
}) => {
  if (activeTab === 'summary') {
    return (
      <div className="summary-container">
        <ProcessingMetadata
          method={method}
          processor={processor}
          backend_processing_time={backend_processing_time}
          total_time={responseTime}
        />
        
        <div className="summary-text">
          {summary.map((sentence, index) => (
            <p key={index} className="summary-sentence">
              {sentence}
            </p>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === 'profiling' && profiling_data) {
    return <ProfilingData data={profiling_data} />;
  }

  return null;
}; 