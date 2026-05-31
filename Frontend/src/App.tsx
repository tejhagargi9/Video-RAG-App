import VideoURLInput from './components/VideoURLInput';

function App() {
  const handleSubmit = async (urlA: string, urlB: string | null) => {
    console.log('YouTube URL:', urlA);
    console.log('Instagram URL:', urlB);

    // Call the ingest endpoint which handles both videos and RAG indexing
    try {
      const response = await fetch('http://127.0.0.1:8000/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          youtube_url: urlA,
          instagram_url: urlB
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
    <VideoURLInput onSubmit={handleSubmit} showSecondInput={true} />
  );
}

export default App;