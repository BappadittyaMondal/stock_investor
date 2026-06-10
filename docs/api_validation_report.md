# API Validation Report

## API Server
- Started on `http://127.0.0.1:8502`

## Auth Validation
- Created a real user through `AuthService.create_user(...)`
- Logged in with a strong password
- Received a valid JWT

## Endpoint Results
- `GET /api/v1/health` -> `200`
- `GET /api/v1/signals` -> `200`
- `GET /api/v1/portfolio` -> `200`
- `GET /api/v1/watchlist` -> `200`
- `GET /api/v1/alerts` -> `200`
- `POST /api/v1/scan` -> `200`
- `POST /api/v1/alert` -> `200`
- Unauthorized `GET /api/v1/portfolio` -> `401`

## Notes
- The REST API imported successfully after adding a safe fallback for the optional RSS parser dependency.
- No endpoint returned an unhandled exception during the live validation run.

