import React, { useState, ChangeEvent, FormEvent } from 'react'
import { Algorithm, ProcessorType } from '../types'
import { InfoIcon } from './InfoIcon'
import { HealthState } from '../hooks/useHealthStatus';

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
      <div className="form-group">
        <div className="label-with-info">
          <label htmlFor="earlyTerminationFactor">
            Early Termination Factor: {earlyTerminationFactor.toFixed(1)}
          </label>
          <InfoIcon 
            tooltip={
              "Controls how much text to process before stopping. " +
              "A higher value (e.g. 5.0) processes more text for potentially better summaries but takes longer. " +
              "A lower value (e.g. 1.5) processes less text for faster results but potentially less accurate summaries."
            }
          />
        </div>
        <input
          type="range"
          id="earlyTerminationFactor"
          min="1.0"
          max="10.0"
          step="0.1"
          value={earlyTerminationFactor}
          onChange={(e) => setEarlyTerminationFactor(parseFloat(e.target.value))}
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
              <option value="default">Default</option>
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
