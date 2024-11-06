import './index.css'

import { useHealthStatus } from './hooks/useHealthStatus'
import { useTheme } from './hooks/useTheme'
import { useFileUpload } from './hooks/useFileUpload'
import { SummaryForm } from './components/SummaryForm'
import { SummaryResult } from './components/SummaryResult'
import { ErrorToast } from './components/ErrorToast'
import { ThemeSwitch } from './components/ThemeSwitch'
import { LoadingBar } from './components/LoadingBar'
import { HealthStatus } from './components/HealthStatus'


function App(): JSX.Element {
  const { healthState, checkHealth, timeLeft, details } = useHealthStatus();
  const { isDarkMode, toggleTheme } = useTheme();
  const {
    result,
    isLoading,
    responseTime,
    error,
    showToast,
    uploadProgress,
    handleSubmit,
    handleCancel,
    handleCloseToast,
  } = useFileUpload();

  return (
    <div className="container">
      <div className="responsive-header">
        <div className="menu-container">
          <HealthStatus 
            checkHealth={checkHealth} 
            timeLeft={timeLeft}
            details={details}
          />
          <ThemeSwitch isDarkMode={isDarkMode} toggleTheme={toggleTheme} />
        </div>
        <h1>File Summarizer</h1>
      </div>
      <p className="subtext">Allowed formats: TXT, MD, EPUB</p>
      <ErrorToast error={error} showToast={showToast} onClose={handleCloseToast} />
      <SummaryForm 
        onSubmit={handleSubmit} 
        isLoading={isLoading} 
        onCancel={handleCancel} 
        healthState={healthState}
      />
      {isLoading && <LoadingBar progress={uploadProgress} onCancel={handleCancel} />}
      <SummaryResult result={result} responseTime={responseTime} />
    </div>
  )
}

export default App
