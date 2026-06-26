import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

// StrictMode намеренно НЕ используется: его dev-режимный двойной mount/unmount
// эффектов рвёт и пересоздаёт игровой WebSocket, из-за чего в сторе оставался
// «осиротевший» сокет и действия (бросок/ответ) переставали отправляться.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>,
);
