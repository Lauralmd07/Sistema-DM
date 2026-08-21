import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const redirect = sessionStorage.getItem('redirect');
if (redirect) {
  sessionStorage.removeItem('redirect');
  const path = redirect.replace(window.location.origin, "") || "/";
  window.history.replaceState(null, "", path);
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
