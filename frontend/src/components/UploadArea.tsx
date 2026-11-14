import React, { useRef, useState, useEffect, useCallback } from 'react';

interface UploadAreaProps {
  onScreen: (file: File) => Promise<void>;
  onClear: () => void;
  isLoading: boolean;
  isBackendOnline: boolean;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  previewUrl: string | null;
  setPreviewUrl: (url: string | null) => void;
  errorMessage: string | null;
  setErrorMessage: (msg: string | null) => void;
  fileName?: string | null;
}

const MAX_BYTES = 10 * 1024 * 1024;

export const UploadArea: React.FC<UploadAreaProps> = ({
  onScreen, onClear, isLoading, isBackendOnline, selectedFile,
  setSelectedFile, previewUrl, setPreviewUrl, errorMessage, setErrorMessage, fileName,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [imageDims, setImageDims] = useState<{ width: number; height: number } | null>(null);

  const handleFile = useCallback((file: File) => {
    setErrorMessage(null);
    if (file.size > MAX_BYTES) { setErrorMessage('Image is too large. Maximum upload size is 10 MB.'); return; }
    if (!file.type.startsWith('image/')) { setErrorMessage('Invalid image file. Upload a JPEG, PNG, or WebP image.'); return; }

    setSelectedFile(file);
    setImageDims(null);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  }, [setErrorMessage, setSelectedFile, setPreviewUrl]);

  useEffect(() => {
    const handlePaste = (event: ClipboardEvent) => {
      const item = Array.from(event.clipboardData?.items ?? []).find((candidate) => candidate.type.startsWith('image/'));
      const file = item?.getAsFile();
      if (file) handleFile(file);
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [handleFile]);

  useEffect(() => {
    if (!previewUrl) return;
    const image = new Image();
    image.onload = () => setImageDims({ width: image.naturalWidth, height: image.naturalHeight });
    image.src = previewUrl;
  }, [previewUrl]);

  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setImageDims(null);
    setErrorMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onClear();
  };
  const openPicker = () => { if (fileInputRef.current) { fileInputRef.current.value = ''; fileInputRef.current.click(); } };
  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`;

  return (
    <section className="acquisition-panel" aria-labelledby="upload-heading">
      <div className="section-heading acquisition-heading">
        <span className="section-index">01</span>
        <div><span className="eyebrow">IMAGE ACQUISITION</span><h2 id="upload-heading">Capture specimen</h2></div>
        <span className={`acquisition-ready ${selectedFile ? 'ready' : ''}`}><i aria-hidden="true" />{selectedFile ? 'Image ready' : 'Awaiting image'}</span>
      </div>

      <input ref={fileInputRef} className="visually-hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { const file = event.target.files?.[0]; if (file) handleFile(file); }} id="pill-file-input" tabIndex={-1} aria-label="Choose a medicine image" />

      <div className={`specimen-viewer ${isDragOver ? 'dragover' : ''} ${previewUrl ? 'has-image' : ''}`} onDragEnter={(event) => { event.preventDefault(); setIsDragOver(true); }} onDragOver={(event) => { event.preventDefault(); setIsDragOver(true); }} onDragLeave={(event) => { event.preventDefault(); setIsDragOver(false); }} onDrop={(event) => { event.preventDefault(); setIsDragOver(false); const file = event.dataTransfer.files[0]; if (file) handleFile(file); }}>
        <div className="viewer-topline"><span><i /> LIVE SPECIMEN VIEW</span><span>RGB / INPUT</span></div>
        {previewUrl ? (
          <div className="specimen-image-stage">
            <span className="viewer-corner corner-tl" /><span className="viewer-corner corner-tr" /><span className="viewer-corner corner-bl" /><span className="viewer-corner corner-br" />
            <img src={previewUrl} alt="Preview of uploaded medicine photograph" className="preview-image" />
            <div className="viewer-coordinate">SPECIMEN · {imageDims ? `${imageDims.width} × ${imageDims.height}` : 'LOADING DIMENSIONS'}</div>
          </div>
        ) : (
          <button type="button" className="dropzone-empty" onClick={openPicker} onDragOver={(event) => event.preventDefault()}>
            <span className="upload-illustration" aria-hidden="true"><svg viewBox="0 0 88 88" fill="none"><rect x="14" y="13" width="60" height="62" rx="13" stroke="currentColor" strokeWidth="1.5"/><path d="M25 60l14-15 9 9 7-8 9 14H25z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/><circle cx="32" cy="32" r="4" stroke="currentColor" strokeWidth="1.6"/><path d="M44 5v12m-6-6h12M79 42h5M4 42h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/><path d="M44 31v20m-7-7 7 7 7-7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg></span>
            <strong>Drop your medicine image here</strong>
            <span>or browse files · paste from clipboard</span>
            <span className="format-note">JPEG, PNG, WEBP <i /> UP TO 10 MB</span>
          </button>
        )}
        <div className="viewer-bottomline"><span>{previewUrl ? fileName || selectedFile?.name : 'NO SPECIMEN LOADED'}</span><span>{selectedFile ? formatSize(selectedFile.size) : 'INPUT 01'}</span></div>
      </div>

      {previewUrl && !selectedFile && <div className="file-inspector"><div className="file-type-icon" aria-hidden="true">IMG</div><div className="file-details"><strong title={fileName || 'Previous session image'}>{fileName || 'Previous session image'}</strong><span>{imageDims ? `${imageDims.width} × ${imageDims.height} px` : 'Session history preview'}</span></div><button type="button" className="icon-control" onClick={openPicker} aria-label="Replace image" title="Choose a new image">↻</button><button type="button" className="icon-control remove-control" onClick={handleClear} aria-label="Remove image" title="Clear result">×</button></div>}
      {selectedFile && <div className="file-inspector"><div className="file-type-icon" aria-hidden="true">IMG</div><div className="file-details"><strong title={fileName || selectedFile.name}>{fileName || selectedFile.name}</strong><span>{imageDims ? `${imageDims.width} × ${imageDims.height} px` : 'Reading image dimensions'} <i /> {formatSize(selectedFile.size)}</span></div><button type="button" className="icon-control" onClick={openPicker} disabled={isLoading} aria-label="Replace image" title="Replace image">↻</button><button type="button" className="icon-control remove-control" onClick={handleClear} disabled={isLoading} aria-label="Remove image" title="Remove image">×</button></div>}

      <div className="acquisition-actions">
        <button type="button" className="scan-button" onClick={() => selectedFile && onScreen(selectedFile)} disabled={!selectedFile || isLoading || !isBackendOnline} aria-busy={isLoading}>
          {isLoading ? <><span className="button-spinner" aria-hidden="true" /> Processing request</> : <><span className="scan-button-icon" aria-hidden="true">⌁</span> Scan Image <span aria-hidden="true">→</span></>}
        </button>
        {!selectedFile && <button type="button" className="browse-button" onClick={openPicker}>Browse files</button>}
      </div>
      <div className="acquisition-note"><span aria-hidden="true">ⓘ</span><span>Place one medicine on a plain surface. Avoid filters, flash and heavy shadows.</span></div>
      {errorMessage && <div className="error-box" role="alert"><strong>Upload issue</strong><span>{errorMessage}</span></div>}
      {!isBackendOnline && <div className="upload-offline-note">The screening service is offline. Your selected image remains in this session.</div>}
    </section>
  );
};
