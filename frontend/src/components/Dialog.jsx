/**
 * Dialog (Modal) Component
 * 
 * A reusable modal dialog component with backdrop, animations, and accessibility features.
 * Supports custom content, actions, and sizes.
 * 
 * @example
 * <Dialog
 *   isOpen={showDialog}
 *   onClose={() => setShowDialog(false)}
 *   title="Confirm Action"
 *   description="Are you sure you want to proceed?"
 * >
 *   <DialogActions>
 *     <Button onClick={onCancel}>Cancel</Button>
 *     <Button variant="primary" onClick={onConfirm}>Confirm</Button>
 *   </DialogActions>
 * </Dialog>
 */

import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export const Dialog = ({ 
  isOpen, 
  onClose, 
  title, 
  description, 
  children,
  size = 'md',
  showCloseButton = true 
}) => {
  const dialogRef = useRef(null);

  // Size variants
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4'
  };

  // Handle ESC key press
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when dialog is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fadeIn" />
      
      {/* Dialog */}
      <div 
        ref={dialogRef}
        className={`
          relative w-full ${sizeClasses[size]}
          bg-slate-800 rounded-lg shadow-2xl
          border border-slate-700
          animate-scaleIn
          max-h-[90vh] overflow-y-auto
        `}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-description"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-slate-700">
          <div className="flex-1">
            {title && (
              <h2 
                id="dialog-title" 
                className="text-xl font-bold text-white"
              >
                {title}
              </h2>
            )}
            {description && (
              <p 
                id="dialog-description" 
                className="mt-2 text-sm text-slate-400"
              >
                {description}
              </p>
            )}
          </div>
          
          {showCloseButton && (
            <button
              onClick={onClose}
              className="
                ml-4 p-1 rounded-md
                text-slate-400 hover:text-white
                hover:bg-slate-700
                transition-colors
                focus:outline-none focus:ring-2 focus:ring-indigo-500
              "
              aria-label="Close dialog"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
};

export const DialogActions = ({ children, align = 'right' }) => {
  const alignClasses = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
    between: 'justify-between'
  };

  return (
    <div className={`flex items-center gap-3 mt-6 ${alignClasses[align]}`}>
      {children}
    </div>
  );
};

// Add animations to global CSS
const styles = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .animate-fadeIn {
    animation: fadeIn 0.2s ease-out;
  }

  .animate-scaleIn {
    animation: scaleIn 0.2s ease-out;
  }
`;
