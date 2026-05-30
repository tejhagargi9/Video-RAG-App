import VideoURLInput from './components/VideoURLInput';

function App() {
  const handleSubmit = async (urlA: string, urlB: string | null) => {
    console.log('YouTube URL:', urlA);
    console.log('Instagram URL:', urlB);

    // Call YouTube backend to get transcript
    try {
      const youtubeResponse = await fetch(`http://127.0.0.1:8000/transcript/${encodeURIComponent(urlA)}`, {
        method: 'GET',
      });

      if (!youtubeResponse.ok) {
        throw new Error(`HTTP error! status: ${youtubeResponse.status}`);
      }

      const youtubeTranscriptData = await youtubeResponse.json();
      console.log('YouTube Transcript:', youtubeTranscriptData);
    } catch (error) {
      console.error('Error fetching YouTube transcript:', error);
    }

    // Call Instagram backend to get transcript (if urlB is provided)
    if (urlB) {
      try {
        const instagramResponse = await fetch(`http://127.0.0.1:8000/instagram-transcript/${encodeURIComponent(urlB)}`, {
          method: 'GET',
        });

        if (!instagramResponse.ok) {
          throw new Error(`HTTP error! status: ${instagramResponse.status}`);
        }

        const instagramTranscriptData = await instagramResponse.json();
        console.log('Instagram Transcript:', instagramTranscriptData);
      } catch (error) {
        console.error('Error fetching Instagram transcript:', error);
      }
    }
  };

  return (
    <VideoURLInput onSubmit={handleSubmit} showSecondInput={true} />
  );
}

export default App;