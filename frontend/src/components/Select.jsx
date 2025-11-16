/**
 * Select Component
 * 
 * A custom dropdown select component with search, multi-select support, and keyboard navigation.
 * Styled to match the application's design system.
 * 
 * @example
 * <Select
 *   options={[
 *     { value: 'pytorch', label: 'PyTorch' },
 *     { value: 'tensorflow', label: 'TensorFlow' }
 *   ]}
 *   value={selectedFramework}
 *   onChange={setSelectedFramework}
 *   placeholder="Select framework"
 * />
 */

import { useState, useRef, useEffect } from 'react';

export const Select = ({
  options = [],
  value,
  onChange,
  placeholder = 'Select...',
  searchable = false,
  multiple = false,
  disabled = false,
  error = null,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const selectRef = useRef(null);
  const searchInputRef = useRef(null);

  // Filter options based on search term
  const filteredOptions = options.filter(option =>
    option.label.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Get display value
  const getDisplayValue = () => {
    if (multiple && Array.isArray(value)) {
      if (value.length === 0) return placeholder;
      return `${value.length} selected`;
    }
    const selected = options.find(opt => opt.value === value);
    return selected ? selected.label : placeholder;
  };

  // Handle option click
  const handleOptionClick = (optionValue) => {
    if (multiple) {
      const newValue = value.includes(optionValue)
        ? value.filter(v => v !== optionValue)
        : [...value, optionValue];
      onChange(newValue);
    } else {
      onChange(optionValue);
      setIsOpen(false);
    }
  };

  // Check if option is selected
  const isSelected = (optionValue) => {
    if (multiple) {
      return value.includes(optionValue);
    }
    return value === optionValue;
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (selectRef.current && !selectRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchTerm('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen && searchable && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen, searchable]);

  return (
    <div ref={selectRef} className={`relative ${className}`}>
      {/* Select Button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          w-full px-4 py-2.5 text-left
          bg-slate-700 border rounded-lg
          text-white
          transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-indigo-500
          ${error ? 'border-red-500' : 'border-slate-600'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-slate-500'}
          ${isOpen ? 'ring-2 ring-indigo-500 border-indigo-500' : ''}
        `}
      >
        <div className="flex items-center justify-between">
          <span className={value ? 'text-white' : 'text-slate-400'}>
            {getDisplayValue()}
          </span>
          <svg
            className={`w-5 h-5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Error Message */}
      {error && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}

      {/* Dropdown */}
      {isOpen && (
        <div className="
          absolute z-50 w-full mt-2
          bg-slate-800 border border-slate-700
          rounded-lg shadow-xl
          max-h-64 overflow-hidden
          animate-slideDown
        ">
          {/* Search Input */}
          {searchable && (
            <div className="p-2 border-b border-slate-700">
              <input
                ref={searchInputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search..."
                className="
                  w-full px-3 py-2
                  bg-slate-700 border border-slate-600
                  rounded-md
                  text-white placeholder-slate-400
                  focus:outline-none focus:ring-2 focus:ring-indigo-500
                "
              />
            </div>
          )}

          {/* Options List */}
          <div className="overflow-y-auto max-h-48">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-sm text-slate-400 text-center">
                No options found
              </div>
            ) : (
              filteredOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleOptionClick(option.value)}
                  className={`
                    w-full px-4 py-2.5 text-left
                    flex items-center justify-between
                    transition-colors
                    ${isSelected(option.value) 
                      ? 'bg-indigo-600 text-white' 
                      : 'text-slate-200 hover:bg-slate-700'
                    }
                  `}
                >
                  <span>{option.label}</span>
                  {isSelected(option.value) && (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Add animation to global CSS
const styles = `
  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-slideDown {
    animation: slideDown 0.2s ease-out;
  }
`;
