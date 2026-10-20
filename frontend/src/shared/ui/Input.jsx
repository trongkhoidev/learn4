import React from 'react';

export const Input = React.forwardRef(({ label, error, hint, icon: Icon, className = '', ...props }, ref) => {
  return (
    <div className="w-full">
      {label && <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>}
      <div className="relative">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Icon className="h-5 w-5 text-slate-400" />
          </div>
        )}
        <input
          ref={ref}
          className={`w-full rounded-md border text-sm transition-colors
            ${Icon ? 'pl-10' : 'pl-3'} pr-3 py-2
            ${error 
              ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500' 
              : 'border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500'
            }
            disabled:bg-slate-50 disabled:text-slate-500
            outline-none
            ${className}`}
          {...props}
        />
      </div>
      {error && <p className="mt-1 text-sm text-red-500">{error}</p>}
      {hint && !error && <p className="mt-1 text-sm text-slate-500">{hint}</p>}
    </div>
  );
});
Input.displayName = 'Input';
