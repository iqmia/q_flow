# Security Scheme

The backend API (q_flow) accepts requests from users possessing a valid jw token. These tokens are obtained and verified through the following steps:

## Application Registration:

1. Register the application with the q_auth service to obtain an app_key and a public_key.
2. Store these keys in the env.json file on the backend to verify tokens:
    a. Use the public key to verify tokens issued by q_auth.
    b. The app_key is necessary only for the frontend to make requests to q_auth.

## Token Handling:

1. Store the same keys (app_key and public_key) on the frontend.
2. When a user logs in or registers on the frontend, the following sequence occurs:
    a. The frontend sends a registration or login request to q_auth using the app_key.
    b. q_auth returns a token for the authenticated user.
    c. The frontend stores this token securely in the user's session (e.g., cookie, secure local storage).
    d. The frontend includes this token in requests sent to the backend (q_flow).
    e. The backend (q_flow) verifies the token using the public_key.

## Process Overview:

### App Registration:

1. Register the application with q_auth to receive app_key and public_key.
2. Store these keys in env.json for the backend and frontend.

### User Authentication:

1. Frontend uses app_key to request user registration/login from q_auth.
2. Frontend receives and securely stores the token from q_auth.
3. Frontend sends requests to q_flow with the token.
4. Backend (q_flow) verifies the token using public_key.

This security scheme ensures that only authenticated users with valid tokens can access the backend API, with token verification being performed by both the frontend and backend.


