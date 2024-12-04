IMPORTANT:
This app has 2 parts:

** #1 Frontend **
 - Has codebase inside "client/" folder
 - It is running on port 5173 and this port should be used for user testing when possible
 - It is a Vite based React app

** #2 Backend **
 - Has codebase inside "server/" folder
 - It is running on port 3000
 - It is an Express app

Concurrently is used to run both client and server together with a single command (`npm run start`).

** IMPORTANT - Mocking data on the frontend **
All API requests from the frontend to the backend must be defined in files inside the api folder (you must never make requests directly from the components)
When you add mock data, make sure to mock the data in files in the api folder and above each mocked API request, add a structure that is expected from the API
Mocking example:

The base client/src/api/api.ts is already created so here are 2 examples for how to write functions to get data from the backend with the mock data:
—EXAMPLE_1 (file `client/src/api/companies.ts`) —
import api from './api';

// Companies List
// GET /companies
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
    // Uncomment the below line to make an actual API call
    // api.get('/api/companies');
}
—END_OF_EXAMPLE_1—

—EXAMPLE_2 (file `client/src/api/domains.ts`) —
import api from './api';

// Add Domain
// POST /domains
// Request: { domain: string, driveLink: string }
// Response: { success: boolean, message: string }
export const addDomain = (data: { domain: string; driveLink: string }) => {
    // Mocking the response
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({success: true, message: 'Domain added successfully'});
        }, 500);
    });
    // Uncomment the below line to make an actual API call
    // return api.post('/domains', data);
}
—END_OF_EXAMPLE_2—
