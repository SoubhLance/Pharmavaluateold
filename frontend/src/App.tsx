import { useState, useEffect, useCallback } from 'react';
import type { ScreenResponse, HealthResponse, ScreenHistoryItem } from './types';
import { API_ENDPOINTS } from './config';
import { Header } from './components/Header';
import { OfflineBanner } from './components/OfflineBanner';
import { UploadArea } from './components/UploadArea';
import { ResultCard } from './components/ResultCard';
import { HistoryList } from './components/HistoryList';
import { AboutMethod } from './components/AboutMethod';

export function App() {
  const [activeTab, setActiveTab] = useState<'screen' | 'about'>('screen');

  // Backend Health & Connectivity
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [isRetryingHealth, setIsRetryingHealth] = useState<boolean>(false);

  // Active Screening State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [currentFileName, setCurrentFileName] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [currentResult, setCurrentResult] = useState<ScreenResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // In-Memory History (strictly in React memory, no localStorage)
  const [history, setHistory] = useState<ScreenHistoryItem[]>([]);
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);

  // Health check query
  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch(API_ENDPOINTS.health, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });
      if (response.ok) {
        const data: HealthResponse = await response.json();
        setHealth(data);
        setIsBackendOnline(true);
      } else {
        setIsBackendOnline(false);
      }
    } catch {
      setIsBackendOnline(false);
    }
  }, []);

  // Poll /health every 10 seconds
  useEffect(() => {
    const initialCheck = setTimeout(checkHealth, 0);
    const interval = setInterval(checkHealth, 10000);
    return () => { clearTimeout(initialCheck); clearInterval(interval); };
  }, [checkHealth]);

  const handleManualHealthRetry = async () => {
    setIsRetryingHealth(true);
    await checkHealth();
    setIsRetryingHealth(false);
  };

  const handleUploadAnother = () => {
    const input = document.getElementById('pill-file-input') as HTMLInputElement | null;
    if (input) {
      input.value = '';
      input.click();
    }
  };

  // Screening execution
  const handleScreenImage = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);
    setCurrentFileName(file.name);

    const formData = new FormData();
    formData.append('file', file, file.name);

    try {
      const response = await fetch(API_ENDPOINTS.screen, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorDetail = `Request failed (${response.status})`;
        try {
          const errData = await response.json();
          if (errData.detail) {
            errorDetail = errData.detail;
          }
        } catch {
          // fallback to status code
        }

        if (response.status === 400) {
          setErrorMessage(
            errorDetail || 'Invalid image file. Upload a valid JPEG, PNG, or WebP image.'
          );
        } else if (response.status === 413) {
          setErrorMessage(
            errorDetail || 'Image is too large. Maximum upload size is 10 MB.'
          );
        } else if (response.status === 503) {
          setErrorMessage('Inference engine is not ready. Please try again shortly.');
        } else {
          setErrorMessage(`Screening error (${response.status}): ${errorDetail}`);
        }
        return;
      }

      const result: ScreenResponse = await response.json();
      setCurrentResult(result);

      // Add to session in-memory history (last 10 items)
      const currentPreview = previewUrl || URL.createObjectURL(file);
      const newItem: ScreenHistoryItem = {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        timestamp: new Date(),
        fileName: file.name,
        thumbnailUrl: currentPreview,
        result,
      };

      setActiveHistoryId(newItem.id);
      setHistory((prev) => [newItem, ...prev.slice(0, 9)]);
    } catch {
      setErrorMessage(
        'Network error: Unable to communicate with screening service at http://127.0.0.1:8000.'
      );
      setIsBackendOnline(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setCurrentResult(null);
    setActiveHistoryId(null);
    setCurrentFileName(null);
  };

  const handleSelectHistoryItem = (item: ScreenHistoryItem) => {
    setActiveHistoryId(item.id);
    setCurrentResult(item.result);
    setSelectedFile(null);
    setPreviewUrl(item.thumbnailUrl);
    setCurrentFileName(item.fileName);
    setErrorMessage(null);
  };

  return (
    <div className="app-root">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        isOnline={isBackendOnline}
      />

      {!isBackendOnline && (
        <OfflineBanner
          onRetry={handleManualHealthRetry}
          isRetrying={isRetryingHealth}
        />
      )}

      <main className="app-container" id={activeTab === 'screen' ? 'screening' : 'method'}>
        {activeTab === 'screen' ? (
          <>
            <div className="workspace-intro"><div><span className="eyebrow">PILL STREAM · VISUAL SCREENING</span><h1>Medicine image intelligence</h1><p>Review image quality and visual consistency against frozen genuine references.</p></div><span className="workspace-id"><i /> LOCAL INFERENCE · FROZEN MODEL</span></div>
            <div className="screening-layout">
              <UploadArea
                onScreen={handleScreenImage}
                onClear={handleClear}
                isLoading={isLoading}
                isBackendOnline={isBackendOnline}
                selectedFile={selectedFile}
                setSelectedFile={setSelectedFile}
                previewUrl={previewUrl}
                setPreviewUrl={setPreviewUrl}
                errorMessage={errorMessage}
                setErrorMessage={setErrorMessage}
                fileName={currentFileName}
              />

              <ResultCard result={currentResult} isLoading={isLoading} onUploadAnother={handleUploadAnother} />
            </div>

            <HistoryList
              history={history}
              activeId={activeHistoryId}
              onSelect={handleSelectHistoryItem}
            />
          </>
        ) : (
          <AboutMethod />
        )}
      </main>

      <footer className="app-footer">
        <span>PHARMAVALUATE · PILL STREAM</span><span>Screening aid only · Verify manually · Not for diagnosis or certification</span><span>FROZEN PIPELINE V1</span>
      </footer>
    </div>
  );
}
export default App;
