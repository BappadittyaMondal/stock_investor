# HFOS v5.0 — PWA Architecture

## Application Structure
HFOS transitions from a standard web application to a Progressive Web App (PWA) via the inclusion of a web app manifest and a Service Worker.

## Key Files
- `frontend/manifest.json`: Defines the installation parameters, icons, display orientation (locked to portrait for mobile), and quick action shortcuts (Scanner, Portfolio).
- `frontend/service_worker.js`: Handles caching and push notifications.
  - **Caching Strategy:** Network First for API routes (ensuring fresh scores). Cache First for static assets (images, CSS).
  - **Fallback:** If offline, serves `/offline.html` containing the last cached portfolio values and watchlist items.

## Cross-Platform Distribution
Because the application runs in a containerized environment and exposes standard HTTP, the PWA architecture makes it trivial to wrap the platform using Capacitor or Tauri later for native App Store deployment on iOS and Android. No backend restructuring will be required.
