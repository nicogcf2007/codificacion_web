import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { uploadFiles, handleAPIError } from '../services/api';
import type { UploadedFiles, UploadResponse } from '../types';

interface FileUploadProps {
  onFilesUploaded: (data: UploadResponse) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFilesUploaded }) => {
  const [files, setFiles] = useState<UploadedFiles>({
    responses: null,
    codes: null,
  });
  const [uploading, setUploading] = useState(false);

  // Dropzone for responses file
  const {
    getRootProps: getResponsesRootProps,
    getInputProps: getResponsesInputProps,
    isDragActive: isResponsesDragActive,
  } = useDropzone({
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    multiple: false,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFiles((prev) => ({ ...prev, responses: acceptedFiles[0] }));
        toast.success(`Archivo de respuestas cargado: ${acceptedFiles[0].name}`);
      }
    },
    onDropRejected: () => {
      toast.error('Archivo inválido. Solo se permiten archivos .xlsx o .xls');
    },
  });

  // Dropzone for codes file
  const {
    getRootProps: getCodesRootProps,
    getInputProps: getCodesInputProps,
    isDragActive: isCodesDragActive,
  } = useDropzone({
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    multiple: false,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFiles((prev) => ({ ...prev, codes: acceptedFiles[0] }));
        toast.success(`Archivo de códigos cargado: ${acceptedFiles[0].name}`);
      }
    },
    onDropRejected: () => {
      toast.error('Archivo inválido. Solo se permiten archivos .xlsx o .xls');
    },
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Codificación de Encuestas con IA
          </h1>
          <p className="text-gray-600">
            Sube tus archivos Excel para comenzar el procesamiento automático
          </p>
        </div>

        <div className="card space-y-6">
          {/* Responses File Dropzone */}
          <div>
            <label className="label">
              Archivo de Respuestas (.xlsx, .xls)
            </label>
            <div
              {...getResponsesRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isResponsesDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : files.responses
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-blue-400'
              }`}
            >
              <input {...getResponsesInputProps()} />
              <div className="space-y-2">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {files.responses ? (
                  <div>
                    <p className="text-green-600 font-medium">
                      ✓ {files.responses.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {(files.responses.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-gray-600">
                      Arrastra el archivo aquí o haz clic para seleccionar
                    </p>
                    <p className="text-sm text-gray-500">
                      Archivo Excel con las respuestas de la encuesta
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Codes File Dropzone */}
          <div>
            <label className="label">
              Archivo de Códigos (.xlsx, .xls)
            </label>
            <div
              {...getCodesRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isCodesDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : files.codes
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-blue-400'
              }`}
            >
              <input {...getCodesInputProps()} />
              <div className="space-y-2">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                {files.codes ? (
                  <div>
                    <p className="text-green-600 font-medium">
                      ✓ {files.codes.name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {(files.codes.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-gray-600">
                      Arrastra el archivo aquí o haz clic para seleccionar
                    </p>
                    <p className="text-sm text-gray-500">
                      Archivo Excel con los códigos de clasificación
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Upload Button */}
          <div className="flex justify-end space-x-4">
            <button
              onClick={() => setFiles({ responses: null, codes: null })}
              disabled={!files.responses && !files.codes}
              className={
                files.responses || files.codes
                  ? 'btn-secondary'
                  : 'btn-disabled'
              }
            >
              Limpiar
            </button>
            <button
              onClick={handleUpload}
              disabled={!files.responses || !files.codes || uploading}
              className={
                files.responses && files.codes && !uploading
                  ? 'btn-primary'
                  : 'btn-disabled'
              }
            >
              {uploading ? (
                <span className="flex items-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Subiendo...
                </span>
              ) : (
                'Cargar Archivos'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  async function handleUpload() {
    if (!files.responses || !files.codes) {
      toast.error('Por favor selecciona ambos archivos');
      return;
    }

    setUploading(true);

    try {
      const response = await uploadFiles(files.responses, files.codes);
      toast.success('Archivos cargados exitosamente');
      onFilesUploaded(response);
    } catch (error) {
      const errorMessage = handleAPIError(error);
      toast.error(`Error al cargar archivos: ${errorMessage}`);
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  }
};

export default FileUpload;
