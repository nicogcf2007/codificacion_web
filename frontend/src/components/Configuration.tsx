import React, { useState } from 'react';
import { toast } from 'react-toastify';
import type { ProcessingConfig } from '../types';

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
  const [maxNewLabels, setMaxNewLabels] = useState(8);
  const [startCode, setStartCode] = useState(501);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredColumns = columns.filter((col) =>
    col.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelectAll = () => {
    if (selectedColumns.length === filteredColumns.length) {
      setSelectedColumns([]);
    } else {
      setSelectedColumns(filteredColumns);
    }
  };

  const handleColumnToggle = (column: string) => {
    setSelectedColumns((prev) =>
      prev.includes(column)
        ? prev.filter((c) => c !== column)
        : [...prev, column]
    );
  };

  const handleStart = () => {
    if (selectedColumns.length === 0) {
      toast.error('Por favor selecciona al menos una columna');
      return;
    }

    if (maxNewLabels < 1) {
      toast.error('El máximo de nuevas etiquetas debe ser mayor a 0');
      return;
    }

    const config: ProcessingConfig = {
      columns: selectedColumns,
      question_column: 'Nombre de la Pregunta',
      max_new_labels: maxNewLabels,
      start_code: startCode,
    };

    onStartProcessing(config);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Configurar Procesamiento
          </h1>
          <p className="text-gray-600">
            Selecciona las columnas a procesar y ajusta los parámetros
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
              <div className="max-h-96 overflow-y-auto space-y-2">
                {filteredColumns.map((column) => (
                  <label
                    key={column}
                    className="flex items-center space-x-3 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedColumns.includes(column)}
                      onChange={() => handleColumnToggle(column)}
                      className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-gray-700">{column}</span>
                  </label>
                ))}
              </div>

              {filteredColumns.length === 0 && (
                <p className="text-center text-gray-500 py-8">
                  No se encontraron columnas
                </p>
              )}
            </div>
          </div>

          {/* Configuration Panel */}
          <div className="space-y-6">
            <div className="card">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Parámetros
              </h2>

              <div className="space-y-4">
                {/* Max New Labels */}
                <div>
                  <label className="label">
                    Máximo de nuevas etiquetas
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={maxNewLabels}
                    onChange={(e) => setMaxNewLabels(parseInt(e.target.value) || 1)}
                    className="input-field"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Número máximo de etiquetas nuevas a crear por pregunta
                  </p>
                </div>

                {/* Start Code */}
                <div>
                  <label className="label">
                    Código inicial para columnas OTRO
                  </label>
                  <input
                    type="number"
                    min="100"
                    max="999"
                    value={startCode}
                    onChange={(e) => setStartCode(parseInt(e.target.value) || 501)}
                    className="input-field"
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    Código de inicio para respuestas en columnas _OTRO
                  </p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="card space-y-3">
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
  );
};

export default Configuration;
