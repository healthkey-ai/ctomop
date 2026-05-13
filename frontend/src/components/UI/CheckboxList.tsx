import React from 'react';

interface CheckboxListProps {
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (selected: string[]) => void;
  disabled?: boolean;
}

export const CheckboxList: React.FC<CheckboxListProps> = ({
  options,
  selected,
  onChange,
  disabled = false,
}) => {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-2 py-1">
      {options.map((option) => (
        <label
          key={option.value}
          className="flex items-center gap-2 cursor-pointer select-none"
        >
          <input
            type="checkbox"
            checked={selected.includes(option.value)}
            onChange={() => toggle(option.value)}
            disabled={disabled}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">{option.label}</span>
        </label>
      ))}
    </div>
  );
};
