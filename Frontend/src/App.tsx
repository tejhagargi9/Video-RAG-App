import { useState, useEffect } from "react";
import VideoURLInput from './components/VideoURLInput';

function App() {
  const [namespace, setNamespace] = useState<string>("");

  // Generate unique namespace on component mount
  useEffect(() => {
    generateNewNamespace();
  }, []);

  const generateNewNamespace = () => {
    // Generate unique namespace: videorag_YYYYMMDD_HHMMSS
    const now = new Date();
    const uniqueId = `videorag_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    localStorage.setItem('videoragnamespace', uniqueId);
    setNamespace(uniqueId);
    return uniqueId;
  };

  const handleSubmit = async (urlA: string, urlB: string | null) => {
    // Generate a new unique namespace for each analyze request
    const currentNamespace = namespace || generateNewNamespace();

    console.log('YouTube URL:', urlA);
    console.log('Instagram URL:', urlB);
    console.log('Namespace:', currentNamespace);

    // Call the ingest endpoint which handles both videos and RAG indexing
    try {
      const response = await fetch('http://127.0.0.1:8000/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: urlA,
          instagram_url: urlB,
          namespace: currentNamespace
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Ingest Result:', data);
    } catch (error) {
      console.error('Error during ingest:', error);
    }
  };

  return (
    <div>
      <div style={{ position: 'fixed', top: 10, right: 10, zIndex: 1000, background: '#18181b', padding: '8px 12px', borderRadius: '8px' }}>
        <span style={{ fontSize: '12px', color: '#a1a1aa' }}>Session: {namespace || 'generating...'}</span>
      </div>
      <VideoURLInput onSubmit={handleSubmit} showSecondInput={true} />
    </div>
  );
}

export default App;