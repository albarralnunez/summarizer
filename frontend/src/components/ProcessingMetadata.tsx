import React from 'react';
import { InfoIcon } from './InfoIcon';

interface ProcessingMetadataProps {
  method: string;
  processor: string;
  backend_processing_time: number;
  total_time: number;
  vocabulary_size?: number;
}

export const ProcessingMetadata: React.FC<ProcessingMetadataProps> = ({
  method,
  processor,
  backend_processing_time,
  total_time,
  vocabulary_size
}) => {
  return (
    <div className="processing-metadata">
      <h3>Processing Details</h3>
      <div className="metadata-grid">
        <div className="metadata-item">
          <div className="metadata-row">
            <InfoIcon tooltip="The summarization algorithm used" />
            <span className="label">Method: {method}</span>
          </div>
        </div>
        <div className="metadata-item">
          <div className="metadata-row">
            <InfoIcon tooltip="The text processing method used" />
            <span className="label">Processor: {processor}</span>
          </div>
        </div>
        <div className="metadata-item">
          <div className="metadata-row">
            <InfoIcon tooltip="Time spent processing on the server" />
            <span className="label">Backend Time: {backend_processing_time.toFixed(2)}s</span>
          </div>
        </div>
        <div className="metadata-item">
          <div className="metadata-row">
            <InfoIcon tooltip="Total time including network transfer" />
            <span className="label">Total Time: {total_time.toFixed(2)}s</span>
          </div>
        </div>
        {vocabulary_size !== undefined && (
          <div className="metadata-item">
            <div className="metadata-row">
              <InfoIcon tooltip="Vocabulary size" />
              <span className="label">Vocabulary Size: {vocabulary_size.toLocaleString()}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 