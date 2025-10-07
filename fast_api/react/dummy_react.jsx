import { useState, useEffect } from "react";

function App() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/")   // call FastAPI backend
      .then((res) => res.json())      // parse JSON
      .then((json) => {
        setData(json.message.data);   // "message" → your dict with data
      })
      .catch((err) => console.error(err));
  }, []);

  return (
    <div>
      <h1>Backend Data</h1>
      {data ? (
        <ul>
          {data.map((item, idx) => (
            <li key={idx}>{item.ticker} - {item.headline}</li>
          ))}
        </ul>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

export default App;
