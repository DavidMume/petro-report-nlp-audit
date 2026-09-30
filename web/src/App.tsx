import { useEffect, useState } from "react";
import { REPO_URL, useData } from "./data";
import { ClaimsPage } from "./pages/ClaimsPage";
import { DocumentPage } from "./pages/DocumentPage";
import { NlpPage } from "./pages/NlpPage";
import { DataPage, MethodologyPage, ProvenancePage, SourcesPage } from "./pages/OtherPages";
import { Overview } from "./pages/Overview";
import { EntitiesPage, TopicsPage } from "./pages/TopicsEntities";
import { VerificationPage } from "./pages/VerificationPage";

const ROUTES: [string, string][] = [
  ["", "Resumen"], ["documento", "Documento"], ["nlp", "NLP"], ["temas", "Temas"], ["entidades", "Entidades"],
  ["afirmaciones", "Afirmaciones"], ["verificacion", "Verificación"], ["procedencia", "Procedencia lingüística"],
  ["datos", "Datos"], ["metodologia", "Metodología"], ["fuentes", "Fuentes"],
];

function parseHash(): { route: string; arg?: string } {
  const h = window.location.hash.replace(/^#\/?/, "");
  const [route, arg] = h.split("/");
  return { route: route || "", arg };
}

export default function App() {
  const { data, error } = useData();
  const [{ route, arg }, setLoc] = useState(parseHash());
  const [theme, setTheme] = useState<string | null>(() => {
    try { return localStorage.getItem("theme"); } catch { return null; }
  });
  useEffect(() => {
    const on = () => { setLoc(parseHash()); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    if (theme) document.documentElement.setAttribute("data-theme", theme);
    else document.documentElement.removeAttribute("data-theme");
    try { theme ? localStorage.setItem("theme", theme) : localStorage.removeItem("theme"); } catch { /* storage unavailable */ }
  }, [theme]);
  const go = (r: string) => { window.location.hash = `#/${r}`; };
  const openClaim = (id: string) => { window.location.hash = `#/afirmaciones/${id}`; };
  const isDark = theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);

  let page = <div className="loading">Cargando datos…</div>;
  if (error) page = <div className="loading">No se pudieron cargar los datos: {error}</div>;
  else if (data) {
    page = {
      "": <Overview d={data} go={go} />,
      documento: <DocumentPage d={data} />,
      nlp: <NlpPage d={data} />,
      temas: <TopicsPage d={data} />,
      entidades: <EntitiesPage d={data} />,
      afirmaciones: <ClaimsPage key={arg || "all"} d={data} initial={arg} />,
      verificacion: <VerificationPage d={data} openClaim={openClaim} />,
      procedencia: <ProvenancePage d={data} />,
      datos: <DataPage d={data} />,
      metodologia: <MethodologyPage d={data} />,
      fuentes: <SourcesPage d={data} />,
    }[route] ?? <Overview d={data} go={go} />;
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#/">Libro de la Verdad · Auditoría</a>
          <nav className="nav" aria-label="Secciones">
            {ROUTES.map(([r, label]) => <a key={r} href={`#/${r}`} className={route === r ? "active" : ""}>{label}</a>)}
          </nav>
          <button className="theme-btn" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label="Cambiar tema">
            {isDark ? "Claro" : "Oscuro"}
          </button>
        </div>
      </header>
      <main className="shell">
        {page}
        <footer className="footer">
          Proyecto independiente de análisis de datos de{" "}
          <a href="https://juandamunoz.com/#projects">Juan David Mume</a> ·{" "}
          <a href={REPO_URL} target="_blank" rel="noreferrer">código y datos</a> · Este sitio no emite una calificación global del
          informe ni de ningún gobierno. Las evaluaciones del piloto están pendientes de revisión humana.
        </footer>
      </main>
    </>
  );
}
