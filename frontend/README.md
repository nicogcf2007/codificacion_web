# Frontend - Sistema de Codificación de Encuestas

Frontend React + TypeScript con interfaz moderna y responsiva.

## Estructura

```
frontend/
├── src/
│   ├── components/       # Componentes React
│   │   ├── FileUpload.tsx
│   │   ├── Configuration.tsx
│   │   ├── ProcessingMonitor.tsx
│   │   └── Results.tsx
│   ├── services/         # Servicios API
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/            # Tipos TypeScript
│   │   └── index.ts
│   ├── App.tsx           # Componente principal
│   ├── main.tsx          # Entry point
│   └── index.css         # Estilos globales
├── package.json
└── vite.config.ts
```

## Instalación

```bash
npm install
```

## Configuración

Copia `.env.example` a `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Ejecución

```bash
npm run dev
```

La aplicación estará disponible en http://localhost:5173

## Build para Producción

```bash
npm run build
```

Los archivos optimizados estarán en `dist/`

## Tecnologías

- React 18
- TypeScript
- TailwindCSS
- Axios (HTTP client)
- Socket.io-client (WebSocket)
- React Dropzone (file uploads)
- React Toastify (notifications)
