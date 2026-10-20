export function Badge({ children, variant = 'gray', className = '', ...props }) {
  const variants = {
    gray: "bg-gray-100 text-gray-800",
    primary: "bg-primary-100 text-primary-800",
    success: "bg-green-100 text-green-800",
    danger: "bg-red-100 text-red-800",
    warning: "bg-yellow-100 text-yellow-800",
    sky: "bg-sky-100 text-sky-800",
    violet: "bg-violet-100 text-violet-800",
    emerald: "bg-emerald-100 text-emerald-800",
    amber: "bg-amber-100 text-amber-800",
    outline: "border border-slate-200 bg-white text-slate-700",
  };

  const classes = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant] || variants.gray} ${className}`;

  return (
    <span className={classes} {...props}>
      {children}
    </span>
  );
}
