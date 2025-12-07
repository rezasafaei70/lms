import React from 'react';
import './Table.css';

export const Table = ({ children, className = '' }) => (
  <div className={`table-container ${className}`}>
    <table className="table">{children}</table>
  </div>
);

export const TableHeader = ({ children }) => (
  <thead className="table-header">{children}</thead>
);

export const TableBody = ({ children }) => (
  <tbody className="table-body">{children}</tbody>
);

export const TableRow = ({ children, onClick, clickable = false, selected = false }) => (
  <tr 
    className={`table-row ${clickable ? 'table-row-clickable' : ''} ${selected ? 'table-row-selected' : ''}`}
    onClick={onClick}
  >
    {children}
  </tr>
);

export const TableHead = ({ children, sortable = false, sorted = null, onSort, className = '' }) => (
  <th 
    className={`table-head ${sortable ? 'table-head-sortable' : ''} ${className}`}
    onClick={sortable ? onSort : undefined}
  >
    <div className="table-head-content">
      {children}
      {sortable && (
        <span className={`table-sort-icon ${sorted ? `sorted-${sorted}` : ''}`}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4L12 8H4L8 4Z" opacity={sorted === 'asc' ? 1 : 0.3} />
            <path d="M8 12L4 8H12L8 12Z" opacity={sorted === 'desc' ? 1 : 0.3} />
          </svg>
        </span>
      )}
    </div>
  </th>
);

export const TableCell = ({ children, className = '' }) => (
  <td className={`table-cell ${className}`}>{children}</td>
);

export const TableEmpty = ({ message = 'داده‌ای یافت نشد', icon }) => (
  <tr>
    <td colSpan="100%" className="table-empty">
      {icon && <div className="table-empty-icon">{icon}</div>}
      <span>{message}</span>
    </td>
  </tr>
);

export default Table;

