import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";
import { describeBbox } from "./geo";

export const HealthContext = createContext({ health: null, error: null });
export const useHealth = () => useContext(HealthContext);

export function useHealthCheck() {
  const [state, setState] = useState({ health: null, error: null });
  useEffect(() => {
    let alive = true;
    const check = () =>
      api
        .health()
        .then((health) => alive && setState({ health, error: null }))
        .catch((e) => alive && setState({ health: null, error: e.message }));
    check();
    const timer = setInterval(check, 15000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);
  return state;
}

/** Imagery dates available at the centre of the selected area (refetched when the area moves). */
export function useAreaDates(bbox) {
  const [state, setState] = useState({ dates: [], loading: false, error: null });
  const key = bbox ? describeBbox(bbox).center.map((v) => v.toFixed(3)).join(",") : null;

  useEffect(() => {
    if (!key) {
      setState({ dates: [], loading: false, error: null });
      return;
    }
    let alive = true;
    const [lat, lon] = key.split(",");
    setState((s) => ({ ...s, loading: true, error: null }));
    const timer = setTimeout(() => {
      api
        .dates(lat, lon)
        .then((dates) => alive && setState({ dates, loading: false, error: null }))
        .catch((e) => alive && setState({ dates: [], loading: false, error: e.message }));
    }, 300);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [key]);
  return state;
}
