// ChatHeader — Deep teal WhatsApp-style header with M1M avatar and icons

export default function ChatHeader() {
  return (
    <header className="flex items-center gap-3 px-4 py-3 bg-m1m-teal shadow-md z-10 flex-shrink-0">
      {/* Back arrow */}
      <button
        aria-label="Back"
        className="text-white/80 hover:text-white transition-colors mr-1"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 5l-7 7 7 7"/>
        </svg>
      </button>

      {/* M1M Avatar — orange circle with bold M1M text */}
      <div className="w-10 h-10 rounded-full bg-m1m-orange flex items-center justify-center flex-shrink-0 shadow-sm">
        <span className="text-white font-bold text-xs tracking-tight leading-none">M1M</span>
      </div>

      {/* Title + status */}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold text-base leading-tight truncate">
          M1M — Munim.ai
        </p>
        <p className="text-white/70 text-xs leading-tight flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block"></span>
          online
        </p>
      </div>

      {/* Action icons — right side */}
      <div className="flex items-center gap-4 text-white/80">
        {/* Video call icon */}
        <button aria-label="Video call" className="hover:text-white transition-colors">
          <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="23 7 16 12 23 17 23 7"/>
            <rect x="1" y="5" width="15" height="14" rx="2"/>
          </svg>
        </button>
        {/* Phone icon */}
        <button aria-label="Voice call" className="hover:text-white transition-colors">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.06 1.23 2 2 0 012.02 1h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 8.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/>
          </svg>
        </button>
        {/* Menu dots */}
        <button aria-label="More options" className="hover:text-white transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/>
          </svg>
        </button>
      </div>
    </header>
  );
}
