import React, { useState } from 'react';

interface VocabularyTooltipProps {
  name: string;
  url: string;
}

export const VocabularyTooltip: React.FC<VocabularyTooltipProps> = ({ name, url }) => {
  const [visible, setVisible] = useState(false);

  const domain = (() => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  })();

  return (
    <span
      className="relative inline-flex items-center ml-1"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <span className="text-blue-400 cursor-help text-xs select-none">ⓘ</span>
      {visible && (
        <span
          className="absolute left-0 top-5 z-50 w-64 rounded shadow-lg bg-gray-800 text-white text-xs p-2 whitespace-normal"
          style={{ pointerEvents: 'none' }}
        >
          <span className="block font-semibold mb-1">Source: {name}</span>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-300 underline break-all"
            style={{ pointerEvents: 'auto' }}
            onClick={(e) => e.stopPropagation()}
          >
            {domain} ↗
          </a>
        </span>
      )}
    </span>
  );
};
