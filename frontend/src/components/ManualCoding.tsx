import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import axios from 'axios';
import { API_URL } from '../services/api';
import type { FrequencyItem, ProcessingConfig } from '../types';

interface ManualCodingProps {
  sessionId: string;
  config: ProcessingConfig;
  onConfirm: (updatedConfig: ProcessingConfig) => void;
  onBack: () => void;
}

const ManualCoding: React.FC<ManualCodingProps> = ({
  sessionId,
  config,
  onConfirm,
  onBack,
}) => {
  const [loading, setLoading] = useState(true);
  const [frequencies, setFrequencies] = useState<Record<string, FrequencyItem[]>>({});
  const [mappings, setMappings] = useState<Record<string, Record<string, string>>>({});
  const [activeTab, setActiveTab] = useState<string>(config.columns[0]?.name || '');

  // Fetch frequencies on mount
  useEffect(() => {
    const fetchFrequencies = async () => {
      try {
        setLoading(true);
        const columnNames = config.columns.map(c => c.name);
        
        const response = await axios.post(`${API_URL}/api/analyze-frequencies`, {
          session_id: sessionId,
          columns: columnNames,
          top_n: 50, // Top 50 frequent answers
          similarity_threshold: 80.0
        });

        setFrequencies(response.data.frequencies);
        
        // Initialize empty mappings
        const initialMappings: Record<string, Record<string, string>> = {};
        columnNames.forEach(col => {
            initialMappings[col] = {};
        });
        setMappings(initialMappings);

      } catch (error) {
        console.error('Error fetching frequencies:', error);
        toast.error('Error al analizar respuestas frecuentes');
      } finally {
        setLoading(false);
      }
    };

    fetchFrequencies();
  }, [sessionId, config]);

  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});

  // ... useEffect ...

  const toggleRow = (itemText: string) => {
    setExpandedRows(prev => ({
      ...prev,
      [itemText]: !prev[itemText]
    }));
  };

  const handleVariationToggle = (column: string, groupText: string, variation: string) => {
    setFrequencies(prev => {
      const colFreqs = prev[column] ? [...prev[column]] : [];
      const itemIndex = colFreqs.findIndex(f => f.text === groupText);
      
      if (itemIndex === -1) return prev;
      
      const item = { ...colFreqs[itemIndex] };
      const currentVariations = [...item.variations];
      
      // If variations has it, remove it (discard). If not, add it back?
      // Wait, we need to know the original variations to add it back.
      // Better to keep a "discarded" set or just remove it from variations.
      // If we remove it, the count should decrease.
      
      // Let's check if it exists in currentVariations
      if (currentVariations.includes(variation)) {
        // Remove it
        item.variations = currentVariations.filter(v => v !== variation);
        item.count--; // Decrease count
        
        // If count becomes 0 or no variations left, maybe remove the group? 
        // Or keep it but it's empty.
      } else {
        // Add it back? This requires storing the original full list somewhere.
        // For simplicity, let's assume we only support discarding for now.
        // If user made a mistake, they might need to reset or we need more complex state.
        // Let's implement "Discard" as "Remove from this group".
        return prev;
      }
      
      colFreqs[itemIndex] = item;
      return { ...prev, [column]: colFreqs };
    });
  };

  const handleCodeChange = (column: string, text: string, code: string) => {
    setMappings(prev => ({
      ...prev,
      [column]: {
        ...prev[column],
        [text]: code
      }
    }));
  };

  const handleFinish = () => {
    // Filter out empty codes
    const cleanMappings: Record<string, Record<string, string>> = {};
    
    Object.keys(mappings).forEach(col => {
        const colMap: Record<string, string> = {};
        const colFreqs = frequencies[col] || [];
        
        Object.entries(mappings[col]).forEach(([text, code]) => {
            if (code && code.trim() !== '') {
                // Find the group to get all variations
                const group = colFreqs.find(f => f.text === text);
                if (group) {
                    // Map representative text
                    colMap[text] = code.trim();
                    // Map ALL variations currently in the group
                    group.variations.forEach(variation => {
                        colMap[variation] = code.trim();
                    });
                } else {
                    // Should not happen if state is consistent, but fallback:
                    colMap[text] = code.trim();
                }
            }
        });
        if (Object.keys(colMap).length > 0) {
            cleanMappings[col] = colMap;
        }
    });

    const updatedConfig = {
        ...config,
        manual_mappings: cleanMappings
    };

    onConfirm(updatedConfig);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600">Analizando respuestas frecuentes...</p>
      </div>
    );
  }

  const currentFrequencies = frequencies[activeTab] || [];

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 flex flex-col">
      <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col">
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Codificación Manual Rápida</h1>
          <p className="text-gray-600 mt-2">
            Asigna códigos a las respuestas más repetidas antes de usar la IA.
            <br />
            <span className="text-sm bg-yellow-100 text-yellow-800 px-2 py-1 rounded mt-1 inline-block">
              Tip: Se aplicará a respuestas similares (&gt;80%) automáticamente.
            </span>
          </p>
        </div>

        <div className="flex-1 bg-white rounded-xl shadow-lg overflow-hidden flex flex-col md:flex-row min-h-[600px]">
          {/* Sidebar - Column List */}
          <div className="w-full md:w-64 bg-gray-50 border-r flex flex-col">
            <div className="p-4 border-b bg-white">
              <h3 className="font-semibold text-gray-700">Preguntas</h3>
            </div>
            <div className="overflow-y-auto flex-1 p-2 space-y-1">
              {config.columns.map(col => (
                <button
                  key={col.name}
                  onClick={() => setActiveTab(col.name)}
                  className={`w-full text-left px-4 py-3 rounded-lg text-sm transition-colors flex justify-between items-center ${
                    activeTab === col.name
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span className="truncate">{col.name}</span>
                  {mappings[col.name] && Object.values(mappings[col.name]).filter(v => v).length > 0 && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${activeTab === col.name ? 'bg-white text-blue-600' : 'bg-blue-100 text-blue-800'}`}>
                      {Object.values(mappings[col.name]).filter(v => v).length}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Main Content - Frequency Table */}
          <div className="flex-1 flex flex-col">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
              <h2 className="text-lg font-semibold text-gray-800">
                Respuestas frecuentes: <span className="text-blue-600">{activeTab}</span>
              </h2>
              <div className="text-sm text-gray-500">
                Mostrando top {currentFrequencies.length}
              </div>
            </div>

            <div className="flex-1 overflow-auto p-0">
              {currentFrequencies.length === 0 ? (
                <div className="h-full flex items-center justify-center text-gray-400">
                  No hay datos suficientes para esta columna
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="bg-gray-100 sticky top-0 z-10 shadow-sm">
                    <tr>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-16">#</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Respuesta (Frecuencia)</th>
                      <th className="p-4 text-xs font-bold text-gray-500 uppercase tracking-wider w-32">Código</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {currentFrequencies.map((item, idx) => (
                      <React.Fragment key={item.text}>
                        <tr 
                          className={`hover:bg-blue-50 transition-colors group cursor-pointer ${expandedRows[item.text] ? 'bg-blue-50' : ''}`}
                          onClick={() => toggleRow(item.text)}
                        >
                          <td className="p-4 text-gray-400 font-mono text-sm">{idx + 1}</td>
                          <td className="p-4">
                            <div className="flex items-center">
                              <span className={`transform transition-transform duration-200 mr-3 text-gray-400 p-1 rounded-full hover:bg-blue-100 hover:text-blue-600 ${expandedRows[item.text] ? 'rotate-90' : ''}`}>
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                </svg>
                              </span>
                              <div className="font-medium text-gray-800">
                                {item.display_text || item.text}
                                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                  x{item.count}
                                </span>
                              </div>
                            </div>
                            {item.variations.length > 1 && !expandedRows[item.text] && (
                              <div className="text-xs text-gray-400 mt-1 ml-6 truncate max-w-lg">
                                {item.variations.length} variaciones: {item.variations.slice(0, 5).join(', ')}...
                              </div>
                            )}
                          </td>
                          <td className="p-4" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="text"
                              placeholder="Ej: 01"
                              maxLength={3}
                              className="w-24 px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center font-mono text-lg transition-all"
                              value={mappings[activeTab]?.[item.text] || ''}
                              onChange={(e) => handleCodeChange(activeTab, item.text, e.target.value)}
                            />
                          </td>
                        </tr>
                        
                        {/* Expanded Variations */}
                        {expandedRows[item.text] && (
                          <tr>
                            <td colSpan={3} className="bg-gray-50 px-8 py-4 border-b border-gray-200">
                              <div className="text-sm font-medium text-gray-700 mb-2">Variaciones agrupadas:</div>
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                {item.variations.map((variation, vIdx) => (
                                  <div key={vIdx} className="flex items-center space-x-2 bg-white p-2 rounded border border-gray-200">
                                    <button 
                                      onClick={() => handleVariationToggle(activeTab, item.text, variation)}
                                      className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50"
                                      title="Descartar variación"
                                    >
                                      ✕
                                    </button>
                                    <span className="text-gray-600 truncate text-sm" title={variation}>
                                      {variation}
                                    </span>
                                  </div>
                                ))}
                              </div>
                              <div className="mt-2 text-xs text-gray-500">
                                * Las variaciones descartadas no recibirán este código y serán procesadas por la IA.
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-between">
          <button
            onClick={onBack}
            className="px-6 py-3 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Atrás
          </button>
          
          <button
            onClick={handleFinish}
            className="px-8 py-3 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transform hover:scale-105 transition-all"
          >
            Confirmar y Procesar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ManualCoding;
