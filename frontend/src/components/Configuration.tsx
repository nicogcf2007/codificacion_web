import React, { useState } from 'react';
import { toast } from 'react-toastify';
import type { ProcessingConfig, ColumnConfig } from '../types';

interface ConfigurationProps {
  columns: string[];
  onStartProcessing: (config: ProcessingConfig) => void;
  onBack: () => void;
}

const Configuration: React.FC<ConfigurationProps> = ({
  columns,
  onStartProcessing,
  onBack,
}) => {
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [columnConfigs, setColumnConfigs] = useState<Record<string, ColumnConfig>>({});
  const [maxNewLabels, setMaxNewLabels] = useState(8);
  // const [startCode, setStartCode] = useState(501); // Removed per requirement
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedColumn, setExpandedColumn] = useState<string | null>(null);

  const filteredColumns = columns.filter((col) =>
    col.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectAll = () => {
    if (selectedColumns.length === filteredColumns.length) {
      setSelectedColumns([]);
      setColumnConfigs({});
    } else {
      setSelectedColumns(filteredColumns);
      const newConfigs: Record<string, ColumnConfig> = {};
      filteredColumns.forEach(col => {
        newConfigs[col] = {
          name: col,
          multiLabel: false,
          maxLabels: 1,
          context: ''
        };
      });
      setColumnConfigs(newConfigs);
    }
  };

  const handleColumnToggle = (column: string) => {
    setSelectedColumns((prev) => {
      const isSelected = prev.includes(column);
      if (isSelected) {
        const newConfigs = { ...columnConfigs };
        delete newConfigs[column];
        setColumnConfigs(newConfigs);
        return prev.filter((c) => c !== column);
      } else {
        setColumnConfigs(prev => ({
          ...prev,
          [column]: {
            name: column,
            multiLabel: false,
            maxLabels: 1,
            context: ''
          }
        }));
        return [...prev, column];
      }
    });
  };

  const updateColumnConfig = (column: string, updates: Partial<ColumnConfig>) => {
    setColumnConfigs(prev => ({
      ...prev,
      [column]: { ...prev[column], ...updates }
    }));
  };

  const handleStart = () => {
    if (selectedColumns.length === 0) {
      toast.error('Por favor selecciona al menos una columna');
      return;
    }

    // if (maxNewLabels < 1) { ... } // Removed validation since 0 is valid

    const finalConfigs = selectedColumns.map(col => ({
      ...columnConfigs[col],
      maxNewLabels: maxNewLabels // Apply global setting to each column
    }));

    const config: ProcessingConfig = {
      columns: finalConfigs,
      question_column: 'Nombre de la Pregunta',
      max_new_labels: maxNewLabels, // Kept for backward compat, but logic uses per-column
      start_code: 501, 
    };

    onStartProcessing(config);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Configurar Procesamiento
          </h1>
          <p className="text-gray-600">
            Selecciona las columnas y configura opciones avanzadas por pregunta
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Column Selection */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-800">
                  Seleccionar Columnas
                </h2>
                <span className="text-sm text-gray-600">
                  {selectedColumns.length} de {columns.length} seleccionadas
                </span>
              </div>

              {/* Search */}
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Buscar columnas..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="input-field"
                />
              </div>

              {/* Select All */}
              <div className="mb-4 pb-4 border-b">
                <label className="flex items-center space-x-3 cursor-pointer hover:bg-gray-50 p-2 rounded">
                  <input
                    type="checkbox"
                    checked={
                      filteredColumns.length > 0 &&
                      selectedColumns.length === filteredColumns.length
                    }
                    onChange={handleSelectAll}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="font-medium text-gray-700">
                    Seleccionar todas
                  </span>
                </label>
              </div>

              {/* Column List */}
              <div className="max-h-[600px] overflow-y-auto space-y-2">
                {filteredColumns.map((column) => {
                  const isSelected = selectedColumns.includes(column);
                  const config = columnConfigs[column];
                  const isExpanded = expandedColumn === column;

                  return (
                    <div key={column} className={`border rounded-lg transition-all ${isSelected ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'}`}>
                      <div className="p-3 flex items-center justify-between">
                        <label className="flex items-center space-x-3 cursor-pointer flex-1">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleColumnToggle(column)}
                            className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                          />
                          <span className="text-gray-700 font-medium">{column}</span>
                        </label>
                        
                        {isSelected && (
                          <button 
                            onClick={() => setExpandedColumn(isExpanded ? null : column)}
                            className="text-blue-600 hover:text-blue-800 text-sm font-medium px-3 py-1"
                          >
                            {isExpanded ? 'Ocultar opciones' : 'Configurar'}
                          </button>
                        )}
                      </div>

                      {/* Advanced Options per Column */}
                      {isSelected && isExpanded && config && (
                        <div className="p-4 border-t border-blue-100 bg-white rounded-b-lg space-y-4 animate-fadeIn">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Multi-label Toggle */}
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                id={`multilabel-${column}`}
                                checked={config.multiLabel}
                                onChange={(e) => updateColumnConfig(column, { multiLabel: e.target.checked })}
                                className="w-4 h-4 text-blue-600 rounded"
                              />
                              <label htmlFor={`multilabel-${column}`} className="text-sm text-gray-700">
                                Permitir múltiples códigos
                              </label>
                            </div>

                            {/* Max Labels Input */}
                            {config.multiLabel && (
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">
                                  Máx. asignaciones
                                </label>
                                <input
                                  type="number"
                                  min="1"
                                  max="10"
                                  value={config.maxLabels}
                                  onChange={(e) => updateColumnConfig(column, { maxLabels: parseInt(e.target.value) || 1 })}
                                  className="input-field py-1 text-sm"
                                />
                              </div>
                            )}
                          </div>

                            {/* Context Textarea */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Contexto para la IA (Opcional)
                            </label>
                            <textarea
                              value={config.context}
                              onChange={(e) => updateColumnConfig(column, { context: e.target.value })}
                              placeholder="Describe de qué trata esta pregunta, qué tipo de respuestas esperas, o da ejemplos..."
                              className="input-field text-sm h-20"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                              Ayuda a la IA a entender mejor el contexto específico de esta pregunta.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {filteredColumns.length === 0 && (
                <p className="text-center text-gray-500 py-8">
                  No se encontraron columnas
                </p>
              )}
            </div>
          </div>

          {/* Global Configuration Panel */}
          <div className="space-y-6">
            <div className="card sticky top-6">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Parámetros Globales
              </h2>

              <div className="space-y-4">
                {/* Max New Labels */}
                <div>
                  <label className="label">
                    Máximo de nuevas etiquetas (Por Pregunta)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={maxNewLabels}
                    onChange={(e) => setMaxNewLabels(parseInt(e.target.value) || 0)}
                    className="input-field"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Límite de nuevas etiquetas permitidas <strong>por cada pregunta</strong>. (0 = Ninguna)
                  </p>
                </div>

                <div className="pt-4 border-t">
                   <p className="text-sm text-gray-600 mb-2">
                     <strong>Resumen:</strong>
                   </p>
                   <ul className="text-sm text-gray-500 space-y-1 list-disc pl-4">
                     <li>{selectedColumns.length} columnas seleccionadas</li>
                     <li>{Object.values(columnConfigs).filter(c => c.multiLabel).length} configuradas como multi-etiqueta</li>
                     <li>{Object.values(columnConfigs).filter(c => c.context).length} con contexto personalizado</li>
                   </ul>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-6 space-y-3">
                <button
                  onClick={handleStart}
                  disabled={selectedColumns.length === 0}
                  className={
                    selectedColumns.length > 0
                      ? 'btn-primary w-full'
                      : 'btn-disabled w-full'
                  }
                >
                  Iniciar Procesamiento
                </button>
                <button onClick={onBack} className="btn-secondary w-full">
                  Volver
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Configuration;