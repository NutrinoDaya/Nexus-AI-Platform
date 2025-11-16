/**
 * Toast Notification Component
 * 
 * A toast notification system for displaying temporary messages.
 * Supports multiple variants (success, error, warning, info) with auto-dismiss.
 * 
 * @example
 * // Using the toast context
 * const { showToast } = useToast();
 * 
 * showToast({
 *   type: 'success',
 *   title: 'Success!',
 *   message: 'Model uploaded successfully',
 *   duration: 3000
 * });
 */

import { createContext, useContext, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';

const ToastContext = createContext(null);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
};

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback(({ type = 'info', title, message, duration = 3000 }) => {
    const id = Date.now();
    const toast = { id, type, title, message };
    
    setToasts(prev => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
};

const ToastContainer = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;

  return createPortal(
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-md">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onClose={() => onRemove(toast.id)} />
      ))}
    </div>,
    document.body
  );
};

const Toast = ({ id, type, title, message, onClose }) => {
  // Toast variants
  const variants = {
    success: {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ),
      className: 'bg-green-600 border-green-500'
    },
    error: {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      ),
      className: 'bg-red-600 border-red-500'
    },
    warning: {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      className: 'bg-amber-600 border-amber-500'
    },
    info: {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      className: 'bg-blue-600 border-blue-500'
    }
  };

  const variant = variants[type] || variants.info;

  return (
    <div className={`
      ${variant.className}
      border-l-4
      rounded-lg shadow-lg
      p-4
      flex items-start gap-3
      animate-slideIn
      backdrop-blur-sm bg-opacity-95
    `}>
      {/* Icon */}
      <div className="flex-shrink-0 text-white">
        {variant.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {title && (
          <h4 className="text-sm font-semibold text-white mb-1">
            {title}
          </h4>
        )}
        {message && (
          <p className="text-sm text-white/90">
            {message}
          </p>
        )}
      </div>

      {/* Close Button */}
      <button
        onClick={onClose}
        className="
          flex-shrink-0 p-1
          text-white/80 hover:text-white
          rounded-md hover:bg-white/10
          transition-colors
          focus:outline-none focus:ring-2 focus:ring-white/50
        "
        aria-label="Close notification"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
};

// Add animation to global CSS
const styles = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .animate-slideIn {
    animation: slideIn 0.3s ease-out;
  }
`;
