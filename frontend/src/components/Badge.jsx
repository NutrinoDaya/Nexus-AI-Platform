/**
 * Badge Component
 * 
 * A versatile badge component for displaying status, counts, and labels.
 * Supports multiple variants, sizes, and pill shapes.
 * 
 * @example
 * <Badge variant="success">Active</Badge>
 * <Badge variant="warning" size="sm">Pending</Badge>
 * <Badge variant="info" pill>New</Badge>
 */

export const Badge = ({ 
  children, 
  variant = 'default', 
  size = 'md',
  pill = false,
  dot = false,
  className = ''
}) => {
  // Variant styles
  const variants = {
    default: 'bg-slate-700 text-slate-200 border-slate-600',
    primary: 'bg-indigo-600 text-white border-indigo-500',
    success: 'bg-green-600 text-white border-green-500',
    warning: 'bg-amber-600 text-white border-amber-500',
    error: 'bg-red-600 text-white border-red-500',
    info: 'bg-blue-600 text-white border-blue-500',
    
    // Subtle variants
    'success-subtle': 'bg-green-900/30 text-green-400 border-green-800',
    'warning-subtle': 'bg-amber-900/30 text-amber-400 border-amber-800',
    'error-subtle': 'bg-red-900/30 text-red-400 border-red-800',
    'info-subtle': 'bg-blue-900/30 text-blue-400 border-blue-800',
  };

  // Size styles
  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };

  return (
    <span className={`
      inline-flex items-center gap-1.5
      ${variants[variant]}
      ${sizes[size]}
      ${pill ? 'rounded-full' : 'rounded-md'}
      border
      font-medium
      ${className}
    `}>
      {dot && (
        <span className={`
          w-1.5 h-1.5 rounded-full
          ${variant === 'success' || variant === 'success-subtle' ? 'bg-green-400' : ''}
          ${variant === 'warning' || variant === 'warning-subtle' ? 'bg-amber-400' : ''}
          ${variant === 'error' || variant === 'error-subtle' ? 'bg-red-400' : ''}
          ${variant === 'info' || variant === 'info-subtle' ? 'bg-blue-400' : ''}
          ${variant === 'primary' ? 'bg-white' : ''}
          ${variant === 'default' ? 'bg-slate-400' : ''}
        `} />
      )}
      {children}
    </span>
  );
};

/**
 * Status Badge Component
 * 
 * Pre-configured badge for common status values.
 * 
 * @example
 * <StatusBadge status="active" />
 * <StatusBadge status="pending" />
 */
export const StatusBadge = ({ status, ...props }) => {
  const statusConfig = {
    active: { variant: 'success', label: 'Active', dot: true },
    inactive: { variant: 'default', label: 'Inactive', dot: true },
    pending: { variant: 'warning', label: 'Pending', dot: true },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'error', label: 'Failed', dot: true },
    running: { variant: 'info', label: 'Running', dot: true },
    cancelled: { variant: 'default', label: 'Cancelled' },
    draft: { variant: 'default', label: 'Draft' },
    archived: { variant: 'default', label: 'Archived' }
  };

  const config = statusConfig[status.toLowerCase()] || { 
    variant: 'default', 
    label: status 
  };

  return (
    <Badge 
      variant={config.variant} 
      dot={config.dot}
      pill
      {...props}
    >
      {config.label}
    </Badge>
  );
};

/**
 * Count Badge Component
 * 
 * Badge for displaying numerical counts.
 * 
 * @example
 * <CountBadge count={5} />
 * <CountBadge count={100} max={99} />
 */
export const CountBadge = ({ count, max = 99, variant = 'primary', ...props }) => {
  const displayCount = count > max ? `${max}+` : count;

  return (
    <Badge variant={variant} pill size="sm" {...props}>
      {displayCount}
    </Badge>
  );
};
