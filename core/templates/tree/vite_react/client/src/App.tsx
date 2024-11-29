import { useState, useEffect } from "react";
import { TriangleRight } from "lucide-react";
import { fetchData } from "./api/Api";
// import { Header } from "./components/Header"
// import { Footer } from "./components/Footer"

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getData = async () => {
      try {
        const result = await fetchData("http://localhost:3000/");
        setData(result);
      } catch (err) {
        setError(err.message);
      }
    };

    getData();
  }, []);

  return (
    <div className="relative min-h-screen bg-background">
      {/* <Header /> */}
      
      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="text-center">
          <TriangleRight className="mx-auto h-24 w-24 text-primary animate-pulse" />
          {error ? (
            // Show error message if there's an error
            <div className="mt-6 text-red-500">
              <h2 className="text-2xl font-bold">Error</h2>
              <p>{error}</p>
            </div>
          ) : data ? (
            // Show data if it's available
            <>
              <h1 className="mt-6 text-3xl font-bold tracking-tight">{data}</h1>
              <p className="mt-2 text-muted-foreground">A modern web experience</p>
            </>
          ) : (
            // Show loading state while waiting for data
            <p className="mt-6 text-xl">Loading...</p>
          )}
        </div>
      </main>

      {/* <Footer /> */}
    </div>
  )
}

export default App
