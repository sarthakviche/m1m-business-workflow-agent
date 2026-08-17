// QuickActionChips — horizontally scrollable pill chips above composer
// Active: Quotation, Invoice — these populate the composer
// Deferred: Dues, Stock, Documents, Tally, Summary — visually disabled

interface Chip {
  id: string;
  label: string;
  active: boolean;
  message: string; // Text to inject into composer when clicked
}

const CHIPS: Chip[] = [
  { id: "hi",        label: "Hi",            active: true,  message: "Hi" },
  { id: "quotation", label: "1 · Quotation", active: true,  message: "Create a quotation for " },
  { id: "invoice",   label: "2 · Invoice",   active: true,  message: "Create an invoice for " },
  { id: "dues",      label: "3 · Dues",      active: false, message: "" },
  { id: "stock",     label: "4 · Stock",     active: false, message: "" },
  { id: "documents", label: "5 · Documents", active: true,  message: "5 · Documents" },
  { id: "tally",     label: "6 · Tally",     active: false, message: "" },
  { id: "summary",   label: "7 · Summary",   active: false, message: "" },
];

interface QuickActionChipsProps {
  onChipClick: (message: string) => void;
}

export default function QuickActionChips({ onChipClick }: QuickActionChipsProps) {
  return (
    <div className="flex-shrink-0 bg-m1m-chat border-t border-black/5">
      <div className="chips-scroll flex gap-2 px-4 py-2.5 overflow-x-auto">
        {CHIPS.map((chip) => (
          <button
            key={chip.id}
            id={`chip-${chip.id}`}
            onClick={() => chip.active && onChipClick(chip.message)}
            disabled={!chip.active}
            title={chip.active ? undefined : "Coming soon"}
            className={[
              "flex-shrink-0 text-sm font-medium px-4 py-1.5 rounded-chip border transition-all",
              chip.active
                ? "bg-white text-m1m-green-text border-m1m-green-text hover:bg-m1m-green/10 active:scale-95 cursor-pointer shadow-sm"
                : "bg-white/50 text-gray-400 border-gray-300 cursor-not-allowed opacity-70",
            ].join(" ")}
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}
