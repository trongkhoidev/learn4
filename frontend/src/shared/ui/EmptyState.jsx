import React from 'react';

export const EmptyState = ({ icon: Icon, title, description, action }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center min-h-[300px] border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
      {Icon && (
        <div className="w-12 h-12 mb-4 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
          <Icon size={24} />
        </div>
      )}
      <h3 className="text-sm font-medium text-slate-900 mb-1">{title}</h3>
      {description && <p className="text-sm text-slate-500 mb-6 max-w-sm">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
};
