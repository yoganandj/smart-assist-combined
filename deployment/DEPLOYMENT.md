# TPF Assistant App Service deployment

This archive is the combined FastAPI and Angular deployment package. Its ZIP
root contains `main.py`, `requirements.txt`, and the built frontend under
`frontend/dist/frontend/browser`; do not wrap these files in another folder.

## App Service configuration

- App Service: **Linux**, **Python 3.13**
- App setting: `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- Startup command:

  ```sh
  python -m uvicorn main:app --host 0.0.0.0 --port 8000
  ```

- App setting: `EASYAUTH_REQUIRED_APP_ROLE=americanusers` (or set the exact
  app-role value to enforce)
- Add the Foundry project/agent and any other backend settings through App
  Service Configuration. Do not add secrets to the ZIP.

For Python 3.13, configure a custom FastAPI startup command in **Settings >
Configuration > General settings > Startup Command**. Enable Microsoft Entra
App Service Authentication (Easy Auth), assign the app role to users/groups,
and keep authentication in front of the API.

## Upload

For Linux App Service, upload the ZIP with the Kudu ZIP Deploy API
(`https://<app-name>.scm.azurewebsites.net/api/zipdeploy`) using the app's
deployment credentials. The Kudu **Zip Push Deploy** browser UI is not
supported for Linux apps. Open **Deployment Center** in Azure portal to monitor
deployment status and logs. Do not choose a source-based build that expects the
Angular source tree; the Angular production bundle is already included.

After deployment, open the app's root URL, verify `/health`, and sign in through
the Easy Auth Microsoft Entra provider. `/auth/me`, `/chat`, and `/chat/stream`
require the configured app role.
