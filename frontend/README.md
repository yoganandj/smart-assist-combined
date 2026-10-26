# TPF Assistant frontend

Standalone Angular UI for the TPF Assistant API.

## Development

Install dependencies and start the Angular dev server:

```sh
npm install
npm start
```

The dev server runs at `http://localhost:4200` and proxies `/auth` and `/chat`
to `http://localhost:8000`. Start the FastAPI backend separately; Easy Auth
sign-in itself requires the app to be deployed behind Azure App Service
Authentication.

## Build and tests

```sh
npm run build
npm run test -- --watch=false
```

The production build is emitted to `dist/frontend/browser`. The backend serves
that bundle from the repository root when it is present. Sign-in and sign-out
use the App Service `/.auth/login/aad` and `/.auth/logout` endpoints, and the
UI uses `/auth/me` to show the current identity and handle missing roles.
