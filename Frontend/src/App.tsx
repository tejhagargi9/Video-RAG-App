import { useState } from "react";
import { useNavigate } from "react-router-dom";
import VideoURLInput from './components/VideoURLInput';

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function generateNamespace(): string {
  const now = new Date();
  return `videorag_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
}

function App() {
  const [namespace] = useState(() => {
    const id = generateNamespace();
    localStorage.setItem('videoragnamespace', id);
    return id;
  });
  const [loadingStatus, setLoadingStatus] = useState<string>("");
  const [isReady, setIsReady] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (urlA: string, urlB: string | null) => {
    setLoadingStatus("Ingesting...");
    setIsReady(false);

    const currentNamespace = namespace;

    console.log('YouTube URL:', urlA);
    console.log('Instagram URL:', urlB);
    console.log('Namespace:', currentNamespace);

    try {
      const response = await fetch(`${API_URL}/ingest`, {
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
      localStorage.setItem('videorag_ingest_data', JSON.stringify(data.results));
      setLoadingStatus("Ready!");
      setIsReady(true);
    } catch (error) {
      console.error('Error during ingest:', error);
      setLoadingStatus("Error");
      setIsReady(false);
    }
  };

  return (
    <div>
      <div style={{ position: 'fixed', top: 10, right: 10, zIndex: 1000, background: '#18181b', padding: '8px 12px', borderRadius: '8px' }}>
        <span style={{ fontSize: '12px', color: '#a1a1aa', marginRight: '8px' }}>Session: {namespace || 'generating...'}</span>
        {loadingStatus && (
          <span style={{ fontSize: '12px', color: isReady ? '#22c55e' : '#f59e0b' }}>
            {loadingStatus}
          </span>
        )}
      </div>
      <VideoURLInput onSubmit={handleSubmit} showSecondInput={true} />
      {isReady && (
        <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 1000 }}>
          <button
            onClick={() => navigate('/chat')}
            style={{ fontSize: 14, color: '#fff', padding: '10px 20px', borderRadius: 8, background: '#4f46e5', border: 'none', cursor: 'pointer' }}
          >
            Open Chat
          </button>
        </div>
      )}
    </div>
  );
}

export default App;