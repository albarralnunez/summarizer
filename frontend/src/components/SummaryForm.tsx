import React, { useState, ChangeEvent, FormEvent } from 'react'
import { Algorithm, ProcessorType, VectorizationType } from '../types'
import { InfoIcon } from './InfoIcon'
import { HealthState } from '../hooks/useHealthStatus';

// Add language type
type Language = 'english' | 'spanish';

interface SummaryFormProps {
  onSubmit: (formData: FormData) => void;
  isLoading: boolean;
  onCancel: () => void;
  healthState: HealthState;
}

export const SummaryForm: React.FC<SummaryFormProps> = ({ onSubmit, isLoading, onCancel, healthState }): JSX.Element => {
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState<string>('')
  const [numSentences, setNumSentences] = useState<number>(3)
  const [earlyTerminationFactor, setEarlyTerminationFactor] = useState<number>(2.0)
  const [algorithm, setAlgorithm] = useState<Algorithm>('default')
  const [processor, setProcessor] = useState<ProcessorType>('default')
  const [enableProfiling, setEnableProfiling] = useState(false);
  const [language, setLanguage] = useState<Language>('english');
  const [computeStatistics, setComputeStatistics] = useState(true);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>): void => {
    if (e.target.files) {
      setFile(e.target.files[0])
      setText('')
    }
  }

  const handleTextChange = (e: ChangeEvent<HTMLTextAreaElement>): void => {
    setText(e.target.value)
    setFile(null)
  }

  const isDaskAvailable = healthState === HealthState.HEALTHY;
  const isFormDisabled = isLoading || healthState === HealthState.UNHEALTHY;

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault()
    if (healthState === HealthState.UNHEALTHY) {
      return
    }

    if (isLoading) {
      onCancel()
      return
    }

    if (!file && !text) {
      return
    }

    const formData = new FormData()
    if (file) {
      formData.append('file', file)
    } else {
      formData.append('text', text)
    }
    formData.append('num_sentences', numSentences.toString())
    formData.append('early_termination_factor', earlyTerminationFactor.toString())
    formData.append('algorithm', algorithm)
    formData.append('processor', processor)
    formData.append('enable_profiling', enableProfiling.toString());
    formData.append('language', language);
    formData.append('compute_statistics', computeStatistics.toString());

    onSubmit(formData)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="file">Select a file:</label>
        <input
          type="file"
          id="file"
          accept=".txt,.md,.epub"
          onChange={handleFileChange}
          disabled={isFormDisabled || !!text}
        />
      </div>
      <div className="form-group">
        <label htmlFor="text">Or enter text:</label>
        <textarea
          id="text"
          value={text}
          onChange={handleTextChange}
          disabled={isFormDisabled || !!file}
          rows={5}
        />
      </div>
      <div className="form-group">
        <label htmlFor="numSentences">Number of sentences in summary:</label>
        <input
          type="number"
          id="numSentences"
          value={numSentences}
          onChange={(e) => setNumSentences(parseInt(e.target.value))}
          min={1}
          disabled={isFormDisabled}
        />
      </div>
      <div className="processing-options">
        <div className="form-group select-group">
          <label htmlFor="algorithm">Summary Algorithm:</label>
          <div className="select-wrapper">
            <select
              id="algorithm"
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value as Algorithm)}
              disabled={isFormDisabled}
            >
              <option value="default">Default (Parallel)</option>
              <option value="simple">Default (Simple)</option>
              <option value="sklearn">Default (Sklearn)</option>
              <option value="dask" disabled={!isDaskAvailable}>
                Dask {!isDaskAvailable && '(unavailable)'}
              </option>
            </select>
          </div>
        </div>
        <div className="form-group select-group">
          <label htmlFor="processor">File Processor:</label>
          <div className="select-wrapper">
            <select
              id="processor"
              value={processor}
              onChange={(e) => setProcessor(e.target.value as ProcessorType)}
              disabled={isFormDisabled}
            >
              <option value="default">Default</option>
              <option value="dask" disabled={!isDaskAvailable}>
                Dask {!isDaskAvailable && '(unavailable)'}
              </option>
            </select>
          </div>
        </div>
      </div>
      <div className="checkbox-grid">
        <div className="checkbox-item">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={computeStatistics}
              onChange={(e) => setComputeStatistics(e.target.checked)}
            />
            Compute Text Statistics
          </label>
        </div>
        <div className="checkbox-item">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={enableProfiling}
              onChange={(e) => setEnableProfiling(e.target.checked)}
            />
            Enable Performance Profiling
          </label>
        </div>
      </div>
      {!computeStatistics && (
        <div className="form-group slider-group">
          <div className="slider-header">
            <span className="slider-title">Early Termination Factor</span>
            <span className="slider-value">{earlyTerminationFactor.toFixed(1)}</span>
          </div>
          <div className="slider-container">
            <input
              type="range"
              id="earlyTerminationFactor"
              value={earlyTerminationFactor}
              onChange={(e) => setEarlyTerminationFactor(parseFloat(e.target.value))}
              min={1.0}
              max={10.0}
              step={0.1}
              disabled={isFormDisabled}
              className="slider"
            />
            <div className="slider-labels">
              <span>1.0</span>
              <span>5.5</span>
              <span>10.0</span>
            </div>
          </div>
          <small className="form-text text-muted">
            Controls how many sentences are processed. Higher values process more sentences but may be slower.
          </small>
        </div>
      )}
      <div className="form-group select-group">
        <label htmlFor="language">Language:</label>
        <div className="select-wrapper">
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            disabled={isFormDisabled}
          >
            <option value="english">English</option>
            <option value="spanish">Spanish</option>
          </select>
        </div>
      </div>
      <div className="button-group">
        <button 
          type="submit"
          disabled={healthState === HealthState.UNHEALTHY || (!file && !text)}
          className={`submit-button ${isLoading ? 'is-canceling' : ''}`}
        >
          {isLoading ? 'Cancel' : 'Summarize'}
        </button>
      </div>
      {healthState === HealthState.UNHEALTHY && (
        <p className="error-message">Server is currently unavailable. Please try again later.</p>
      )}
      {healthState === HealthState.DEGRADED && (
        <p className="warning-message">Some features are currently unavailable. Basic functionality remains operational.</p>
      )}
    </form>
  )
}
