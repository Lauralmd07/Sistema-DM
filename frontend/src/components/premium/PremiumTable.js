import React, { useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
} from '@tanstack/react-table';
import { ArrowUp, ArrowDown, ChevronsUpDown } from 'lucide-react';
import { premiumTheme } from '../../theme-premium';
import { motion } from 'framer-motion';

export const PremiumTable = ({
  data,
  columns,
  className = '',
  onRowClick,
  virtualized = false,
}) => {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div 
      className={`overflow-hidden rounded-xl ${className}`}
      style={{
        background: premiumTheme.background.tertiary,
        border: `1px solid ${premiumTheme.border.primary}`,
      }}
    >
      {/* Table Header */}
      <div 
        className="overflow-x-auto"
        style={{ backgroundColor: premiumTheme.background.secondary }}
      >
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-6 py-4 text-left text-xs font-medium uppercase tracking-wider"
                    style={{ color: premiumTheme.gold.matte }}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={`flex items-center space-x-2 ${
                          header.column.getCanSort() ? 'cursor-pointer select-none' : ''
                        }`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <span>
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                        </span>
                        {header.column.getCanSort() && (
                          <span>
                            {{
                              asc: <ArrowUp className=\"w-4 h-4\" />,
                              desc: <ArrowDown className=\"w-4 h-4\" />,
                            }[header.column.getIsSorted()] ?? (
                              <ChevronsUpDown className=\"w-4 h-4 opacity-30\" />
                            )}
                          </span>
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody 
            className="divide-y"
            style={{ borderColor: premiumTheme.border.primary }}
          >
            {table.getRowModel().rows.map((row, idx) => (
              <motion.tr
                key={row.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
                className={`transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
                style={{
                  ':hover': {
                    backgroundColor: premiumTheme.background.quaternary,
                  },
                }}
                onClick={() => onRowClick?.(row.original)}
                data-testid={`table-row-${row.id}`}
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className=\"px-6 py-4 text-sm\"
                    style={{ color: premiumTheme.text.primary }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty state */}
      {table.getRowModel().rows.length === 0 && (
        <div 
          className=\"text-center py-12\"
          style={{ color: premiumTheme.text.tertiary }}
        >
          <p>Nenhum registro encontrado</p>
        </div>
      )}
    </div>
  );
};
