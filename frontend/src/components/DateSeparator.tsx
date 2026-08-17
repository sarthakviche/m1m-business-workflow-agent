// DateSeparator — centered "Today" pill, matches WhatsApp date separator

interface DateSeparatorProps {
  label?: string;
}

export default function DateSeparator({ label = "Today" }: DateSeparatorProps) {
  return (
    <div className="flex justify-center my-4 select-none">
      <span className="bg-white/80 text-gray-500 text-xs font-medium px-3 py-1 rounded-full shadow-sm">
        {label}
      </span>
    </div>
  );
}
