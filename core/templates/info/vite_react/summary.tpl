IMPORTANT:
This app has 2 parts:

** #1 Frontend **
    * ReactJS based frontend in `client/` folder using Vite devserver
    * Integrated shadcn-ui component library with Tailwind CSS framework
    * Client-side routing using `react-router-dom` with page components defined in `client/src/pages/` and other components in `client/src/components`
    * It is running on port 5173 and this port should be used for user testing when possible
    * All requests to the backend need to go to an endpoint that starts with `/api/` (e.g. `/api/companies`)
    * Implememented pages:
        * Home - home (index) page (`/`){% if options.auth %}
        * Login - login page (`/login/`) - on login, stores the auth tokens to `accessToken` and `refreshToken` variables in local storage
        * Register - register page (`/register/`) - on register, store **ONLY** the `accessToken` variable in local storage{% endif %}

** #2 Backend **
    * Express-based server implementing REST API endpoints in `api/`
    * Has codebase inside "server/" folder
    * Backend is running on port 3000
    * MongoDB database support with Mongoose{% if options.auth %}
    * Token-based authentication (using bearer access and refresh tokens)
    * User authentication (email + password):
        * login/register API endpoints in `/server/routes/auth.js`
        * authorization middleware in `/server/routes/middleware/auth.js`
        * user management logic in `/server/routes/services/user.js`
        * User authentication is implemented and doesn't require any additional work{% endif %}


Concurrently is used to run both client and server together with a single command (`npm run start`).

** IMPORTANT - Mocking data on the frontend **
All API requests from the frontend to the backend must be defined in files inside the api folder (you must never make requests directly from the components) and the data must be mocked during the frontend implementation. Make sure to always add an API request whenever something needs to be sent or fetched from the backend.
When you add mock data, make sure to mock the data in files in the `client/src/api` folder and above each mocked API request, add a structure that is expected from the API with fields `Description`, `Endpoint`, `Request`, and `Response`. You **MUST NOT** add mock data anywhere else in the frontend codebase.
Mocking example:

The base client/src/api/api.ts is already created so here are 2 examples for how to write functions to get data from the backend with the mock data:
—EXAMPLE_1 (file `client/src/api/companies.ts`) —
import api from './api';

// Description: Get a list of Companies
// Endpoint: GET /api/companies
// Request: {}
// Response: { companies: Array<{ domain: string, name: string, lastContact: string }> }
export const getCompanies = () => {
    // Mocking the response
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                companies: [
                    {domain: 'google.com', name: 'Google', lastContact: '2021-08-01'},
                    {domain: 'facebook.com', name: 'Facebook', lastContact: '2021-08-02'},
                    {domain: 'microsoft.com', name: 'Microsoft', lastContact: '2021-08-03'},
                ],
            });
        }, 500);
    });
    // Uncomment the below lines to make an actual API call
    // try {
    //   return await api.get('/api/companies', data);
    // } catch (error) {
    //   throw new Error(error?.response?.data?.error || error.message);
    // }
}
—END_OF_EXAMPLE_1—

—EXAMPLE_2 (file `client/src/api/work.ts`) —
import api from './api';

// Description: Add a new Work
// Endpoint: POST /api/work
// Request: { work: string, driveLink: string }
// Response: { success: boolean, message: string }
export const addWork = (data: { work: string; driveLink: string }) => {
    // Mocking the response
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({success: true, message: 'Work added successfully'});
        }, 500);
    });
    // Uncomment the below lines to make an actual API call
    // try {
    //   return await api.post('/api/work/add', data);
    // } catch (error) {
    //   throw new Error(error?.response?.data?.error || error.message);
    // }
}
—END_OF_EXAMPLE_2—

Whenever you add an API request from the frontend, make sure to wrap the request in try/catch block and in the catch block, return `throw new Error(error?.response?.data?.message || error.message);` - in the place where the API request function is being called, show a toast message with an error.

**IMPORTANT**
Mongodb is being used as a database so whenever you need to take an `id` of an object on frontend, make sure to take `_id`. For example, if you have a company object, whenever you want to set an id for an element, you should get `company._id` instead of `company.id`.
