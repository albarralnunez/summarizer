import React from 'react';
import { InfoIcon } from './InfoIcon';


interface MemoryDetail {
  file: string;
  line: number;
  size: number;
  count: number;
}

interface FunctionProfile {
  function_name: string;
  total_time: number;
  total_exec_time: number;
  percentage: number;
  calls: number;
  memory_per_call: number;
}

interface ProfilingDataItem {
  functions: FunctionProfile[];
  memory_usage: number;
  memory_peak: number;
  memory_details: MemoryDetail[];
}

interface ProfilingDataProps {
  data: ProfilingDataItem;
}

export const ProfilingData: React.FC<ProfilingDataProps> = ({ data }) => {

  if (!data) return null;

  return (
    <div className="profiling-data">
      {/* Memory Usage Section */}
      <div className="memory-metrics">
        <h4 className="section-header">
          <InfoIcon tooltip="Detailed memory consumption metrics during the summarization process" />
          Memory Usage
        </h4>
        <p className="total-memory">
          <span className="metric-label">Total Memory:</span>
          {data.memory_usage.toFixed(2)} MB
        </p>
        <p className="peak-memory">
          <span className="metric-label">Peak Memory:</span>
          {data.memory_peak.toFixed(2)} MB
        </p>
      </div>

      {/* Memory Details Section */}
      <div className="memory-details">
        <h4>Memory Hotspots</h4>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Line</th>
                <th>Size (MB)</th>
                <th>Allocations</th>
              </tr>
            </thead>
            <tbody>
              {data.memory_details.map((detail, index) => (
                <tr key={index}>
                  <td data-label="File">{detail.file}</td>
                  <td data-label="Line">{detail.line}</td>
                  <td data-label="Size">{detail.size.toFixed(2)}</td>
                  <td data-label="Allocations">{detail.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Function Profiles Section */}
      <h4>Function Profiles</h4>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Function</th>
              <th>Time/Call (s)</th>
              <th>Total Time (s)</th>
              <th>Memory/Call (MB)</th>
              <th>Percentage</th>
              <th>Calls</th>
            </tr>
          </thead>
          <tbody>
            {data.functions.map((func, index) => (
              <tr key={index}>
                <td data-label="Function">{func.function_name}</td>
                <td data-label="Time/Call">{func.total_time.toFixed(4)}</td>
                <td data-label="Total Time">{func.total_exec_time.toFixed(4)}</td>
                <td data-label="Memory/Call">{func.memory_per_call.toFixed(2)}</td>
                <td data-label="Percentage">{func.percentage.toFixed(2)}%</td>
                <td data-label="Calls">{func.calls}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}; 