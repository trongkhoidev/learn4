import React from 'react';

export const Textarea = React.forwardRef(({ label, error, hint, showCount, maxLength, className = '', value, ...props }, ref) => {
  return (
    <div className="w-full">
      {label && <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>}
      <div className="relative">
        <textarea
          ref={ref}
          value={value}
          maxLength={maxLength}
          className={`w-full rounded-md border text-sm transition-colors px-3 py-2
            ${error 
              ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500' 
              : 'border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            }
            disabled:bg-slate-50 disabled:text-slate-500
            outline-none
            ${className}`}
          {...props}
        />
        {showCount && (
          <div className="absolute bottom-2 right-2 text-xs text-slate-400 bg-white/80 px-1 rounded">
            {value?.length || 0}{maxLength ? ` / ${maxLength}` : ''}
          </div>
        )}
      </div>
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
      {hint && !error && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
});
Textarea.displayName = 'Textarea';
