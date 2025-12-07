import React, { useState, useRef, useEffect } from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, isToday, getDay } from 'date-fns-jalali';
import { faIR } from 'date-fns-jalali/locale';
import { toPersianDigits, jalaliMonths, jalaliWeekdays, gregorianToJalaliInput, jalaliToGregorian } from '../../utils/jalaliDate';
import './JalaliDatePicker.css';

const JalaliDatePicker = ({
  value,
  onChange,
  label,
  placeholder = 'انتخاب تاریخ',
  disabled = false,
  minDate,
  maxDate,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [viewDate, setViewDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(null);
  const containerRef = useRef(null);

  // Initialize selected date from value
  useEffect(() => {
    if (value) {
      const date = typeof value === 'string' ? new Date(value) : value;
      setSelectedDate(date);
      setViewDate(date);
    }
  }, [value]);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handlePrevMonth = () => {
    setViewDate(subMonths(viewDate, 1));
  };

  const handleNextMonth = () => {
    setViewDate(addMonths(viewDate, 1));
  };

  const handleDateSelect = (date) => {
    setSelectedDate(date);
    setIsOpen(false);
    if (onChange) {
      // Return ISO string for API compatibility
      onChange(date.toISOString().split('T')[0]);
    }
  };

  const renderCalendar = () => {
    const monthStart = startOfMonth(viewDate);
    const monthEnd = endOfMonth(viewDate);
    const days = eachDayOfInterval({ start: monthStart, end: monthEnd });
    
    // Get the day of week for the first day (0 = Saturday in Jalali)
    const startDayOfWeek = getDay(monthStart);
    
    // Create empty slots for days before the first day
    const emptySlots = Array(startDayOfWeek).fill(null);
    
    const monthName = format(viewDate, 'MMMM', { locale: faIR });
    const year = format(viewDate, 'yyyy', { locale: faIR });

    return (
      <div className="jalali-calendar">
        {/* Header */}
        <div className="calendar-header">
          <button type="button" onClick={handleNextMonth} className="nav-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
          <span className="month-year">{monthName} {toPersianDigits(year)}</span>
          <button type="button" onClick={handlePrevMonth} className="nav-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </div>

        {/* Weekdays */}
        <div className="calendar-weekdays">
          {jalaliWeekdays.map((day) => (
            <span key={day}>{day[0]}</span>
          ))}
        </div>

        {/* Days */}
        <div className="calendar-days">
          {emptySlots.map((_, index) => (
            <span key={`empty-${index}`} className="day-cell empty" />
          ))}
          {days.map((day) => {
            const isSelected = selectedDate && isSameDay(day, selectedDate);
            const isTodayDate = isToday(day);
            const isDisabled = (minDate && day < minDate) || (maxDate && day > maxDate);
            
            return (
              <button
                key={day.toISOString()}
                type="button"
                className={`day-cell ${isSelected ? 'selected' : ''} ${isTodayDate ? 'today' : ''} ${isDisabled ? 'disabled' : ''}`}
                onClick={() => !isDisabled && handleDateSelect(day)}
                disabled={isDisabled}
              >
                {toPersianDigits(format(day, 'd', { locale: faIR }))}
              </button>
            );
          })}
        </div>

        {/* Today Button */}
        <div className="calendar-footer">
          <button
            type="button"
            className="today-btn"
            onClick={() => handleDateSelect(new Date())}
          >
            امروز
          </button>
        </div>
      </div>
    );
  };

  const displayValue = selectedDate
    ? toPersianDigits(format(selectedDate, 'yyyy/MM/dd', { locale: faIR }))
    : '';

  return (
    <div className={`jalali-date-picker ${className}`} ref={containerRef}>
      {label && <label className="date-picker-label">{label}</label>}
      <div className="date-picker-input-wrapper">
        <input
          type="text"
          className="date-picker-input"
          value={displayValue}
          placeholder={placeholder}
          onClick={() => !disabled && setIsOpen(true)}
          readOnly
          disabled={disabled}
        />
        <span className="date-picker-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </span>
      </div>
      {isOpen && !disabled && (
        <div className="calendar-dropdown">
          {renderCalendar()}
        </div>
      )}
    </div>
  );
};

export default JalaliDatePicker;

