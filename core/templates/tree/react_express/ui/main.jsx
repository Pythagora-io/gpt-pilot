{% if options.auth %}
import axios from 'axios'
{% endif %}
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, useLocation } from "react-router-dom"

import './index.css'

// Pages in the app
import Home from './pages/Home.jsx'
{% if options.auth %}
import Register from './pages/Register.jsx'
import Login from './pages/Login.jsx'

// Add auth token to every API request if we have it
axios.interceptors.request.use(config => {
  const token = localStorage.getItem("token");
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})
{% endif %}

function PageNotFound() {
  const { pathname } = useLocation()
  return (
    <div className="w-full h-screen flex flex-col items-center justify-center px-4">
      <h1 className="font-bold">Page Not Found</h1>
      <p className="text-center">
        Page <code>{pathname}</code> does not exist.
        <br />
        <a href="/" className="underline">Go home</a>
      </p>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <Home />,
  },
{% if options.auth %}
  {
    path: "/register/",
    element: <Register />,
  },
  {
    path: "/login/",
    element: <Login />,
  },
{% endif %}
  {
    path: "*",
    element: <PageNotFound />,
  }
])

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
