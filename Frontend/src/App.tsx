import VideoURLInput from './components/VideoURLInput';

function App() {
  const handleSubmit = (urlA: string, urlB: string) => {
    console.log('YouTube URL:', urlA);
    console.log('Instagram URL:', urlB);
    // Add your own logic here if needed
  };

  return (
    <VideoURLInput onSubmit={handleSubmit} />
  );
}

export default App;