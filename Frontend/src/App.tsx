import VideoURLInput from './components/VideoURLInput';

function App() {
  const handleSubmit = async (urlA: string, urlB: string | null) => {
    // In transcript mode, urlB will be null
    console.log('YouTube URL:', urlA);
    
    // Call backend to get transcript
    try {
      const response = await fetch(`http://127.0.0.1:8000/transcript/${encodeURIComponent(urlA)}`, {
        method: 'GET',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const transcriptData = await response.json();
      console.log('Transcript:', transcriptData);
    } catch (error) {
      console.error('Error fetching transcript:', error);
    }
  };

  return (
    <VideoURLInput onSubmit={handleSubmit} showSecondInput={false} />
  );
}

export default App;