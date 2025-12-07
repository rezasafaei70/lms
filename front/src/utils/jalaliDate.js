/**
 * Jalali (Persian) Date Utilities
 * Uses date-fns-jalali for Jalali calendar support
 */

import { format, parse, isValid } from 'date-fns-jalali';
import { faIR } from 'date-fns-jalali/locale';

// Persian digits
const persianDigits = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
const englishDigits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];

/**
 * Convert English digits to Persian
 */
export const toPersianDigits = (str) => {
  if (!str) return str;
  return String(str).replace(/\d/g, (d) => persianDigits[parseInt(d)]);
};

/**
 * Convert Persian digits to English
 */
export const toEnglishDigits = (str) => {
  if (!str) return str;
  return String(str).replace(/[۰-۹]/g, (d) => englishDigits[persianDigits.indexOf(d)]);
};

/**
 * Format date to Jalali string
 * @param {Date|string|number} date - Date to format
 * @param {string} formatStr - Format string (default: 'yyyy/MM/dd')
 * @returns {string} Formatted Jalali date with Persian digits
 */
export const formatJalali = (date, formatStr = 'yyyy/MM/dd') => {
  if (!date) return '';
  
  try {
    const dateObj = typeof date === 'string' || typeof date === 'number' 
      ? new Date(date) 
      : date;
    
    if (!isValid(dateObj)) return '';
    
    const formatted = format(dateObj, formatStr, { locale: faIR });
    return toPersianDigits(formatted);
  } catch (error) {
    console.error('Error formatting date:', error);
    return '';
  }
};

/**
 * Format date to Jalali with time
 * @param {Date|string|number} date - Date to format
 * @returns {string} Formatted Jalali date and time
 */
export const formatJalaliDateTime = (date) => {
  return formatJalali(date, 'yyyy/MM/dd - HH:mm');
};

/**
 * Format date to Jalali with weekday name
 * @param {Date|string|number} date - Date to format
 * @returns {string} Formatted Jalali date with weekday
 */
export const formatJalaliWithDay = (date) => {
  return formatJalali(date, 'EEEE، d MMMM yyyy');
};

/**
 * Format relative time (e.g., "۲ روز پیش")
 * @param {Date|string|number} date - Date to format
 * @returns {string} Relative time string
 */
export const formatRelativeTime = (date) => {
  if (!date) return '';
  
  try {
    const dateObj = typeof date === 'string' || typeof date === 'number' 
      ? new Date(date) 
      : date;
    
    if (!isValid(dateObj)) return '';
    
    const now = new Date();
    const diffInSeconds = Math.floor((now - dateObj) / 1000);
    
    if (diffInSeconds < 60) return 'همین الان';
    if (diffInSeconds < 3600) return `${toPersianDigits(Math.floor(diffInSeconds / 60))} دقیقه پیش`;
    if (diffInSeconds < 86400) return `${toPersianDigits(Math.floor(diffInSeconds / 3600))} ساعت پیش`;
    if (diffInSeconds < 604800) return `${toPersianDigits(Math.floor(diffInSeconds / 86400))} روز پیش`;
    
    return formatJalali(dateObj);
  } catch (error) {
    return '';
  }
};

/**
 * Get current Jalali date string for input
 * @returns {string} Current date in yyyy-MM-dd format
 */
export const getCurrentJalaliDate = () => {
  return format(new Date(), 'yyyy-MM-dd', { locale: faIR });
};

/**
 * Convert Jalali date string to Gregorian Date object
 * @param {string} jalaliStr - Jalali date string (yyyy/MM/dd or yyyy-MM-dd)
 * @returns {Date|null} Gregorian Date object
 */
export const jalaliToGregorian = (jalaliStr) => {
  if (!jalaliStr) return null;
  
  try {
    const normalizedStr = toEnglishDigits(jalaliStr).replace(/\//g, '-');
    const parsed = parse(normalizedStr, 'yyyy-MM-dd', new Date(), { locale: faIR });
    return isValid(parsed) ? parsed : null;
  } catch (error) {
    console.error('Error converting Jalali to Gregorian:', error);
    return null;
  }
};

/**
 * Convert Gregorian Date to Jalali string for input
 * @param {Date|string} date - Gregorian date
 * @returns {string} Jalali date string for input (yyyy-MM-dd with English digits)
 */
export const gregorianToJalaliInput = (date) => {
  if (!date) return '';
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    if (!isValid(dateObj)) return '';
    
    return format(dateObj, 'yyyy-MM-dd', { locale: faIR });
  } catch (error) {
    return '';
  }
};

/**
 * Get Jalali month names
 */
export const jalaliMonths = [
  'فروردین', 'اردیبهشت', 'خرداد',
  'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر',
  'دی', 'بهمن', 'اسفند'
];

/**
 * Get Jalali weekday names
 */
export const jalaliWeekdays = [
  'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'
];

/**
 * Format a date from API (ISO string) to display format
 * @param {string} isoDate - ISO date string from API
 * @returns {string} Formatted Jalali date
 */
export const formatApiDate = (isoDate) => {
  if (!isoDate) return '-';
  return formatJalali(isoDate);
};

/**
 * Format a datetime from API (ISO string) to display format
 * @param {string} isoDate - ISO datetime string from API
 * @returns {string} Formatted Jalali datetime
 */
export const formatApiDateTime = (isoDate) => {
  if (!isoDate) return '-';
  return formatJalaliDateTime(isoDate);
};

export default {
  formatJalali,
  formatJalaliDateTime,
  formatJalaliWithDay,
  formatRelativeTime,
  getCurrentJalaliDate,
  jalaliToGregorian,
  gregorianToJalaliInput,
  toPersianDigits,
  toEnglishDigits,
  formatApiDate,
  formatApiDateTime,
  jalaliMonths,
  jalaliWeekdays,
};

