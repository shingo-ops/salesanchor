import React, { type ReactNode } from 'react';
import './data-list.css';

export type DataListColumn = { id: string; label: string; minWidth: string; visible: boolean };

export function DataList<Row>({ columns, rows, getRowKey, renderCell, onRowSelect }: { columns: DataListColumn[]; rows: Row[]; getRowKey: (row: Row) => string; renderCell: (row: Row, column: DataListColumn) => ReactNode; onRowSelect?: (row: Row) => void }) {
  const visibleColumns = columns.filter((column) => column.visible);
  return <div className="data-list" role="list" style={{ '--data-list-column-count': visibleColumns.length } as React.CSSProperties}><div className="data-list-header" aria-hidden="true">{visibleColumns.map((column) => <div key={column.id} style={{ minWidth: column.minWidth }}>{column.label}</div>)}</div><div className="data-list-body">{rows.map((row) => <button className="data-list-row" role="listitem" type="button" key={getRowKey(row)} onClick={() => onRowSelect?.(row)}>{visibleColumns.map((column) => <span key={column.id} style={{ minWidth: column.minWidth }}>{renderCell(row, column)}</span>)}</button>)}</div></div>;
}
