import React, { useState } from 'react';
import { TextStatistics } from './TextStatistics';
import { ProfilingData } from './ProfilingData';
import { ProcessingMetadata } from './ProcessingMetadata';

interface SummaryResultProps {
  result: {
    summary: string[];
    method: string;
    processor: string;
    backend_processing_time: number;
    compute_statistics: boolean;
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
    text_statistics?: {
      word_count: number;
      sentence_count: number;
      unique_words: number;
      avg_word_length: number;
      avg_sentence_length: number;
      most_common_words: [string, number][];
      top_scoring_words: [string, number][];
      vocabulary_size: number;
    };
  } | null;
  responseTime: number;
}

type Tab = 'summary' | 'profiling' | 'statistics';

export const SummaryResult: React.FC<SummaryResultProps> = (
  { result, responseTime }
) => {
  const [activeTab, setActiveTab] = useState<Tab>('summary');
  
  if (!result) return null;

  return (
    <div className="summary-result">
      <div className="processing-details">
        <ProcessingMetadata
          method={result.method}
          processor={result.processor}
          backend_processing_time={result.backend_processing_time}
          total_time={responseTime}
          vocabulary_size={result.text_statistics?.vocabulary_size}
        />
      </div>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          📝 Summary
        </button>
        {result.compute_statistics && result.text_statistics && (
          <button 
            className={`tab ${activeTab === 'statistics' ? 'active' : ''}`}
            onClick={() => setActiveTab('statistics')}
          >
            📊 Statistics
          </button>
        )}
        {result.profiling_data && (
          <button 
            className={`tab ${activeTab === 'profiling' ? 'active' : ''}`}
            onClick={() => setActiveTab('profiling')}
          >
            ⚡ Profiling Data
          </button>
        )}
      </div>

      <div className="tab-content">
        {activeTab === 'summary' && (
          <div className="summary-text">
            {result.summary.map((sentence, index) => (
              <p key={index} className="summary-sentence">
                {sentence}
              </p>
            ))}
          </div>
        )}
        {activeTab === 'statistics' && result.compute_statistics && result.text_statistics && (
          <TextStatistics statistics={result.text_statistics} />
        )}
        {activeTab === 'profiling' && result.profiling_data && (
          <ProfilingData data={result.profiling_data} />
        )}
      </div>
    </div>
  );
};
