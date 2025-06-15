import { useState } from "react";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  return (
    <main className="p-4">
      <h1>File Upload Console (stub)</h1>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      {file && <p>Selected: {file.name} ({file.size} bytes)</p>}
    </main>
  );
}
