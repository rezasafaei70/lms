import React, { useState, useRef, useEffect, useCallback } from 'react';
import './AutocompleteSelect.css';

/**
 * AutocompleteSelect - Search and select from large datasets
 */
const AutocompleteSelect = ({
  label,
  value,
  onChange,
  onSearch,
  options: initialOptions = [],
  displayField = 'name',
  valueField = 'id',
  placeholder = 'جستجو کنید...',
  disabled = false,
  required = false,
  hint,
  minSearchLength = 1,
  debounceMs = 300,
  noResultsText = 'نتیجه‌ای یافت نشد',
  loadingText = 'در حال جستجو...',
  clearable = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [options, setOptions] = useState(initialOptions);
  const [loading, setLoading] = useState(false);
  const [selectedOption, setSelectedOption] = useState(null);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [hasSearched, setHasSearched] = useState(false);
  
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const debounceRef = useRef(null);

  // Get display text for an option
  const getDisplayText = useCallback((option) => {
    if (!option) return '';
    if (typeof displayField === 'function') {
      return displayField(option);
    }
    return option[displayField] || '';
  }, [displayField]);

  // Get value for an option
  const getValue = useCallback((option) => {
    if (!option) return null;
    return option[valueField];
  }, [valueField]);

  // Perform search
  const performSearch = useCallback(async (query) => {
    if (!onSearch) return;
    
    console.log('AutocompleteSelect: performSearch called with:', query);
    setLoading(true);
    setHasSearched(true);
    
    try {
      const results = await onSearch(query);
      console.log('AutocompleteSelect: Got results:', results?.length || 0);
      setOptions(results || []);
    } catch (error) {
      console.error('AutocompleteSelect: Search error:', error);
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, [onSearch]);

  // Find selected option from value
  useEffect(() => {
    if (value) {
      const found = options.find(opt => getValue(opt) === value);
      if (found) {
        setSelectedOption(found);
      }
    } else {
      setSelectedOption(null);
    }
  }, [value, options, getValue]);

  // Update options when initialOptions change
  useEffect(() => {
    if (initialOptions.length > 0) {
      setOptions(initialOptions);
    }
  }, [initialOptions]);

  // Handle search with debounce
  useEffect(() => {
    if (!onSearch) return;
    
    // Clear previous debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Check minimum search length (but allow empty for initial load)
    if (searchQuery.length > 0 && searchQuery.length < minSearchLength) {
      return;
    }

    // Debounce the search
    debounceRef.current = setTimeout(() => {
      performSearch(searchQuery);
    }, searchQuery.length === 0 ? 0 : debounceMs);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [searchQuery, onSearch, minSearchLength, debounceMs, performSearch]);

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchQuery('');
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev < options.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : prev);
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && options[highlightedIndex]) {
          handleSelect(options[highlightedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSearchQuery('');
        break;
      default:
        break;
    }
  };

  // Scroll highlighted item into view
  useEffect(() => {
    if (listRef.current && highlightedIndex >= 0) {
      const item = listRef.current.children[highlightedIndex];
      if (item) {
        item.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex]);

  const handleSelect = (option) => {
    setSelectedOption(option);
    onChange(getValue(option));
    setIsOpen(false);
    setSearchQuery('');
    setHighlightedIndex(-1);
  };

  const handleClear = (e) => {
    e.stopPropagation();
    setSelectedOption(null);
    onChange(null);
    setSearchQuery('');
  };

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    console.log('AutocompleteSelect: Input changed to:', newValue);
    setSearchQuery(newValue);
    if (!isOpen) setIsOpen(true);
    setHighlightedIndex(-1);
  };

  const handleInputFocus = () => {
    if (!disabled) {
      setIsOpen(true);
      // Trigger initial search if no options and haven't searched yet
      if (options.length === 0 && !hasSearched && !loading && searchQuery === '') {
        performSearch('');
      }
    }
  };

  // Handle click on selected option to allow re-searching
  const handleSelectedClick = () => {
    if (!disabled) {
      setIsOpen(true);
      setSearchQuery('');
      inputRef.current?.focus();
    }
  };

  return (
    <div className="autocomplete-select" ref={containerRef}>
      {label && (
        <label className="autocomplete-label">
          {label}
          {required && <span className="autocomplete-required">*</span>}
        </label>
      )}
      
      <div 
        className={`autocomplete-input-container ${isOpen ? 'is-open' : ''} ${disabled ? 'is-disabled' : ''}`}
        onClick={() => !disabled && inputRef.current?.focus()}
      >
        {selectedOption && !isOpen ? (
          <div className="autocomplete-selected" onClick={handleSelectedClick} style={{ cursor: 'pointer' }}>
            <span className="autocomplete-selected-text">
              {getDisplayText(selectedOption)}
            </span>
            {clearable && !disabled && (
              <button 
                type="button"
                className="autocomplete-clear-btn"
                onClick={handleClear}
                tabIndex={-1}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        ) : (
          <input
            ref={inputRef}
            type="text"
            className="autocomplete-input"
            value={searchQuery}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
          />
        )}
        
        <div className="autocomplete-icon">
          {loading ? (
            <svg className="autocomplete-spinner" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" strokeDasharray="60" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          )}
        </div>
      </div>

      {isOpen && (
        <div className="autocomplete-dropdown" ref={listRef}>
          {loading ? (
            <div className="autocomplete-loading">{loadingText}</div>
          ) : options.length === 0 ? (
            <div className="autocomplete-no-results">
              {!hasSearched 
                ? 'در حال بارگذاری...'
                : searchQuery.length > 0 && searchQuery.length < minSearchLength 
                  ? `حداقل ${minSearchLength} کاراکتر وارد کنید`
                  : noResultsText
              }
            </div>
          ) : (
            options.map((option, index) => (
              <div
                key={getValue(option) || index}
                className={`autocomplete-option ${highlightedIndex === index ? 'is-highlighted' : ''} ${getValue(option) === value ? 'is-selected' : ''}`}
                onClick={() => handleSelect(option)}
                onMouseEnter={() => setHighlightedIndex(index)}
              >
                {getDisplayText(option)}
              </div>
            ))
          )}
        </div>
      )}

      {hint && <div className="autocomplete-hint">{hint}</div>}
    </div>
  );
};

export default AutocompleteSelect;

