// WaQuickChips — horizontally scrollable quick-action chips above composer
// Mirrors the exact same chip set as the main frontend.
// Active chips: Hi, Quotation, Invoice, Documents
// Grayed-out (coming soon): Dues, Stock, Tally, Summary

interface Chip {
  id: string;
  label: string;
  active: boolean;
  message: string;
}

const CHIPS: Chip[] = [
  { id: 'hi',        label: 'Hi',            active: true,  message: 'Hi' },
  { id: 'quotation', label: '1 · Quotation', active: true,  message: 'Create a quotation for ' },
  { id: 'invoice',   label: '2 · Invoice',   active: true,  message: 'Create an invoice for ' },
  { id: 'dues',      label: '3 · Dues',      active: false, message: '' },
  { id: 'stock',     label: '4 · Stock',     active: false, message: '' },
  { id: 'documents', label: '5 · Documents', active: true,  message: '5 · Documents' },
  { id: 'tally',     label: '6 · Tally',     active: false, message: '' },
  { id: 'summary',   label: '7 · Summary',   active: false, message: '' },
];

interface WaQuickChipsProps {
  onChipClick: (message: string) => void;
}

export default function WaQuickChips({ onChipClick }: WaQuickChipsProps) {
  return (
    <div className="flex-shrink-0 bg-[#f0f0f0] border-t border-black/8">
      <div className="chips-no-scrollbar flex gap-2 px-3 py-2 overflow-x-auto">
        {CHIPS.map((chip) => (
          <button
            key={chip.id}
            onClick={() => chip.active && onChipClick(chip.message)}
            disabled={!chip.active}
            title={chip.active ? undefined : 'Coming soon'}
            className={[
              'flex-shrink-0 text-sm font-medium px-3.5 py-1.5 rounded-full border transition-all',
              chip.active
                ? 'bg-white text-[#128C7E] border-[#128C7E] hover:bg-[#e8f5f2] active:scale-95 cursor-pointer shadow-sm'
                : 'bg-white/60 text-gray-400 border-gray-300 cursor-not-allowed opacity-60',
            ].join(' ')}
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}
