// WaDateSeparator — "TODAY" pill between conversations (WhatsApp style)

interface WaDateSeparatorProps {
  label: string;
}

export default function WaDateSeparator({ label }: WaDateSeparatorProps) {
  return (
    <div className="flex items-center justify-center py-3 select-none">
      <span className="bg-[#e1f3fb] text-gray-600 text-[12px] font-medium px-3 py-1 rounded-full shadow-sm">
        {label}
      </span>
    </div>
  );
}
