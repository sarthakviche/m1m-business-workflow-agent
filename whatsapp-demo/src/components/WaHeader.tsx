// WaHeader — pixel-accurate WhatsApp chat header for the Munim demo

interface WaHeaderProps {
  onBack?: () => void;
}

export default function WaHeader({ onBack }: WaHeaderProps) {
  return (
    <header className="flex items-center gap-2.5 px-2 py-2 bg-[#128C7E] flex-shrink-0 z-10 select-none">
      {/* Back arrow */}
      <button
        aria-label="Back"
        onClick={onBack}
        className="text-white/90 hover:text-white transition-colors p-1 -ml-1"
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 5l-7 7 7 7" />
        </svg>
      </button>

      {/* Avatar */}
      <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center flex-shrink-0 shadow-sm overflow-hidden">
        <img src="/munim-logo.png" alt="Munim" className="w-full h-full object-cover" />
      </div>

      {/* Contact info */}
      <div className="flex-1 min-w-0 -ml-0.5">
        <p className="text-white font-semibold text-[15px] leading-tight truncate">
          Munim — M1M Business
        </p>
        <p className="text-white/75 text-[12px] leading-tight flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-green-300 inline-block" />
          online
        </p>
      </div>

      {/* Right icons */}
      <div className="flex items-center gap-3 text-white/90 pr-1">

        {/* Three dots menu */}
        <button aria-label="More options" className="hover:text-white transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5" />
            <circle cx="12" cy="12" r="1.5" />
            <circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </div>
    </header>
  );
}
