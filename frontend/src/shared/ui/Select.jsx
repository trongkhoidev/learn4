import React from 'react';

export const Select = React.forwardRef(({ label, error, hint, options = [], className = '', ...props }, ref) => {
  return (
    <div className="w-full">
      {label && <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>}
      <select
        ref={ref}
        className={`w-full rounded-md border text-sm transition-colors px-3 py-2 bg-white
          ${error 
            ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500' 
            : 'border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
          }
          disabled:bg-slate-50 disabled:text-slate-500
          outline-none
          ${className}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
      {hint && !error && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
});
Select.displayName = 'Select';
