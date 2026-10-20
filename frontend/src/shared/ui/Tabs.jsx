import React, { createContext, useContext, useState } from 'react';

const TabsContext = createContext({});

export const Tabs = ({ defaultValue, value, onValueChange, children, className = '' }) => {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const activeValue = value !== undefined ? value : internalValue;
  const setActiveValue = onValueChange || setInternalValue;

  return (
    <TabsContext.Provider value={{ activeValue, setActiveValue }}>
      <div className={`w-full ${className}`}>{children}</div>
    </TabsContext.Provider>
  );
};

export const TabsList = ({ children, className = '' }) => {
  return (
    <div className={`flex space-x-1 border-b border-slate-200 mb-4 ${className}`}>
      {children}
    </div>
  );
};

export const TabsTrigger = ({ value, children, className = '' }) => {
  const { activeValue, setActiveValue } = useContext(TabsContext);
  const isActive = activeValue === value;

  return (
    <button
      type="button"
      onClick={() => setActiveValue(value)}
      className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 
        ${isActive 
          ? 'border-blue-600 text-blue-600' 
          : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
        } ${className}`}
    >
      {children}
    </button>
  );
};

export const TabsContent = ({ value, children, className = '' }) => {
  const { activeValue } = useContext(TabsContext);
  if (activeValue !== value) return null;
  return <div className={`outline-none ${className}`}>{children}</div>;
};
