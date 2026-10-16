/**
 * 閲覧ページ（/viewer/）の入口。アプリ本体（App.tsx・components.css・本体の辞書）は読み込まない。
 * 全体の CSS は index.css（デザイントークン）だけを読む。
 */
import "./i18n";
import "../../index.css";
import "./viewer.css";
import React from "react";
import ReactDOM from "react-dom/client";
import ViewerApp from "./ViewerApp";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ViewerApp />
  </React.StrictMode>,
);
