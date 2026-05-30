import { useState } from "react";

const YT_PATTERN = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)[A-Za-z0-9_-]{11}/;
const IG_PATTERN = /^(https?:\/\/)?(www\.)?instagram\.com\/(reel|reels|p)\/[A-Za-z0-9_-]+/;

export default function VideoURLInput({ onSubmit }) {
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");

  const aValid = YT_PATTERN.test(urlA.trim());
  const bValid = IG_PATTERN.test(urlB.trim());
  const canSubmit = aValid && bValid;

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-xl space-y-3">

        <div className="mb-6">
          <h1 className="text-xl font-semibold text-zinc-100 tracking-tight">Compare Videos</h1>
          <p className="text-sm text-zinc-500 mt-1">Paste a YouTube and Instagram Reel URL to begin</p>
        </div>

        {/* YouTube */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-bold tracking-widest text-indigo-400 bg-indigo-950 border border-indigo-800 px-2 py-0.5 rounded">A</span>
            <span className="text-xs text-zinc-500">YouTube</span>
            {urlA && (aValid
              ? <span className="ml-auto text-xs text-emerald-500">✓ valid</span>
              : <span className="ml-auto text-xs text-red-400">✗ invalid</span>)}
          </div>
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="currentColor">
              <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2C0 8.1 0 12 0 12s0 3.9.5 5.8a3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1C24 15.9 24 12 24 12s0-3.9-.5-5.8zM9.8 15.5V8.5l6.2 3.5-6.2 3.5z"/>
            </svg>
            <input
              type="url"
              value={urlA}
              onChange={e => setUrlA(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              className="w-full bg-zinc-950 border border-zinc-800 focus:border-zinc-600 rounded-lg pl-9 pr-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-700 outline-none transition-colors font-mono"
            />
          </div>
        </div>

        {/* Instagram */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-bold tracking-widest text-rose-400 bg-rose-950 border border-rose-800 px-2 py-0.5 rounded">B</span>
            <span className="text-xs text-zinc-500">Instagram Reels</span>
            {urlB && (bValid
              ? <span className="ml-auto text-xs text-emerald-500">✓ valid</span>
              : <span className="ml-auto text-xs text-red-400">✗ invalid</span>)}
          </div>
          <div className="relative">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-pink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
              <circle cx="12" cy="12" r="4"/>
              <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
            </svg>
            <input
              type="url"
              value={urlB}
              onChange={e => setUrlB(e.target.value)}
              placeholder="https://instagram.com/reel/..."
              className="w-full bg-zinc-950 border border-zinc-800 focus:border-zinc-600 rounded-lg pl-9 pr-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-700 outline-none transition-colors font-mono"
            />
          </div>
        </div>

        <button
          onClick={() => canSubmit && onSubmit?.(urlA.trim(), urlB.trim())}
          disabled={!canSubmit}
          className={`w-full py-3 rounded-xl text-sm font-semibold transition-all mt-2
            ${canSubmit
              ? "bg-zinc-100 text-zinc-900 hover:bg-white cursor-pointer"
              : "bg-zinc-900 text-zinc-600 border border-zinc-800 cursor-not-allowed"}`}
        >
          {canSubmit ? "Analyze Both Videos →" : aValid ? "Add Instagram Reel URL" : bValid ? "Add YouTube URL" : "Paste both URLs to continue"}
        </button>

      </div>
    </div>
  );
}