import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./theme.css";
import "./styles.css";

const pageColor = getComputedStyle(document.documentElement).getPropertyValue("--color-page").trim();
document.querySelector('meta[name="theme-color"]')?.setAttribute("content", pageColor);

ReactDOM.createRoot(document.getElementById("app")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
