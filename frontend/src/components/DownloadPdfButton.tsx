// DownloadPdfButton — Orange button linking to the generated PDF

interface DownloadPdfButtonProps {
  pdfUrl?: string | null;
}

export default function DownloadPdfButton({ pdfUrl }: DownloadPdfButtonProps) {
  if (!pdfUrl) return null;

  function handleClick() {
    if (!pdfUrl) return;
    // Open the PDF in a new tab / window using the existing backend-served route
    window.open(pdfUrl, "_blank", "noopener,noreferrer");
  }

  return (
    <button
      onClick={handleClick}
      type="button"
      className="w-full mt-3.5 bg-m1m-orange hover:bg-m1m-orange-dark active:scale-[0.99] text-white text-xs font-semibold py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer"
    >
      {/* Document / PDF icon */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
      <span>Download PDF</span>
    </button>
  );
}
