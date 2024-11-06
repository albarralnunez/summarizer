export interface SummaryResultType {
  summary: string[];
  backend_processing_time: number;
}

export type ApiResponse<T> = {
  data: T | null;
  error: string | null;
}

export type Algorithm = 'default' | 'dask' | 'simple' | 'sklearn';
export type ProcessorType = 'default' | 'dask';
export type VectorizationType = 'default' | 'simple';

export interface SummaryResponse {
  summary: string[];
  method: Algorithm;
  backend_processing_time: number;
  processor?: ProcessorType;
}

export interface SummaryOutput {
  summary: string[];
  method: Algorithm;
  processor?: ProcessorType;
  backend_processing_time: number;
}
