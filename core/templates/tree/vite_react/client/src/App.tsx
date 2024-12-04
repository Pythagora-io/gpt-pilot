import { useState, useEffect } from "react";
import { TriangleRight } from "lucide-react";
// import { Header } from "./components/Header"
// import { Footer } from "./components/Footer"

function App() {
  return (
    <div className="relative min-h-screen bg-background">
      {/* <Header /> */}

      <main className="flex min-h-screen items-center justify-center p-4">
        <div className="text-center">
          <TriangleRight className="mx-auto h-24 w-24 text-primary animate-pulse" />
          <h1 className="mt-6 text-3xl font-bold tracking-tight">{{ project_name }}</h1>
          <p className="mt-2 text-muted-foreground">A modern web experience</p>
        </div>
      </main>

      {/* <Footer /> */}
    </div>
  )
}

export default App
