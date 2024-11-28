IMPORTANT:
This app has 2 parts:

#1 Frontend
 - Has codebase inside "client/" folder
 - It is running on port 5173 and this port should be used for user testing when possible
 - It is a Vite based React app

#2 Backend
 - Has codebase inside "server/" folder
 - It is running on port 3000
 - It is an Express app

Concurrently is used to run both client and server together with a single command (`npm run start`).
