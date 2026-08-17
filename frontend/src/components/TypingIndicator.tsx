// TypingIndicator — animated three-dot assistant "typing" state

export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 px-4 py-1 max-w-[80%]">
      <div className="relative bg-white rounded-bubble rounded-bl-sm px-4 py-3 shadow-bubble flex items-center gap-1">
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block"></span>
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block"></span>
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block"></span>
      </div>
    </div>
  );
}
