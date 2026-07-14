import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ChessGame } from "../app/components/ChessGame";
import "../app/globals.css";

const root = document.getElementById("root");
if (!root) throw new Error("Neural Chess root element is missing");

createRoot(root).render(
  <StrictMode>
    <ChessGame />
  </StrictMode>,
);
