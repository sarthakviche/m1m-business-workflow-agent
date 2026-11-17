// WaTypingIndicator — three animated dots shown while Munim is "typing"

export default function WaTypingIndicator() {
  return (
    <div className="flex items-end gap-1.5 px-3 py-1">
      {/* Incoming bubble (left-aligned) */}
      <div className="relative bg-white rounded-[7.5px] rounded-bl-none px-3.5 py-2.5 shadow-bubble flex items-center gap-1">
        {/* Bubble tail */}
        <span className="bubble-in" />
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block" />
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block" />
        <span className="typing-dot w-2 h-2 rounded-full bg-gray-400 inline-block" />
      </div>
    </div>
  );
}
