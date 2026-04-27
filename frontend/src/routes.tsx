import { createBrowserRouter, Navigate } from "react-router-dom";
import { App } from "@/App";
import { LoginGate } from "@/components/LoginGate";
import { EventsView } from "@/components/EventsView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/events" replace /> },
      { path: "login", element: <LoginGate /> },
      { path: "events", element: <EventsView /> },
    ],
  },
]);
