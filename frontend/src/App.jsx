import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const call = async (path, method = "GET", body) => {
  const r = await fetch(API + path, {
    method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Erreur serveur");
  return r.status === 204 ? null : r.json();
};
const STATUS = { nouvelle: "Nouvelle", en_cours: "En cours", resolue: "Résolue" };
const Badge = ({ kind, children }) => <span className={`badge ${kind}`}>{children}</span>;

export default function App() {
  const [view, setView] = useState("dashboard");
  const [customers, setCustomers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({});
  const [calls, setCalls] = useState([]);
  const [error, setError] = useState("");

  const refresh = async () => {
    try {
      const [c, t, s, k] = await Promise.all([call("/customers"), call("/tickets"), call("/stats"), call("/calls")]);
      setCustomers(c); setTickets(t); setStats(s); setCalls(k); setError("");
    } catch { setError("API injoignable : lance le backend (uvicorn main:app --reload)."); }
  };
  useEffect(() => { refresh(); }, []);
  const act = async (fn) => { try { await fn(); await refresh(); } catch (e) { setError(e.message); } };

  const nav = [["dashboard", "Tableau de bord"], ["tickets", "Demandes"], ["customers", "Clients"], ["calls", "Appels"]];
  return (
    <div className="app">
      <aside>
        <div className="logo"><span className="smile">◡</span> SmartDesk</div>
        {nav.map(([k, l]) => (
          <button key={k} className={view === k ? "nav active" : "nav"} onClick={() => setView(k)}>{l}</button>
        ))}
      </aside>
      <main>
        {error && <div className="alert">{error}</div>}
        {view === "dashboard" && <Dashboard stats={stats} tickets={tickets} />}
        {view === "customers" && <Customers customers={customers} act={act} />}
        {view === "tickets" && <Tickets tickets={tickets} customers={customers} act={act} />}
        {view === "calls" && <Calls calls={calls} customers={customers} act={act} />}
      </main>
    </div>
  );
}

function Dashboard({ stats, tickets }) {
  const cards = [
    ["Demandes", stats.total, "yellow"], ["Urgentes à traiter", stats.urgentes_a_traiter, "rose"],
    ["En cours", stats.en_cours, "blue"], ["Résolues", stats.resolues, "mint"], ["Prospects chauds", stats.prospects_chauds, "yellow"],
  ];
  const urgent = tickets.filter((t) => t.priority === "haute" && t.status !== "resolue");
  return (<>
    <h1>Tableau de bord</h1><p className="muted">Vue d'ensemble de la relation client.</p>
    <div className="cards">{cards.map(([l, v, c]) => (
      <div key={l} className={`card stat ${c}`}><span>{l}</span><strong>{v ?? 0}</strong></div>))}</div>
    <h2>À traiter en priorité</h2>
    <div className="panel">
      {urgent.length === 0 && <p className="muted">Rien d'urgent. Bravo !</p>}
      {urgent.map((t) => (
        <div className="row" key={t.id}><div><b>{t.subject}</b><div className="muted">{t.customer_name}</div></div>
          <Badge kind="rose">Haute</Badge></div>))}
    </div>
  </>);
}

function Customers({ customers, act }) {
  const empty = { name: "", email: "", company: "" };
  const [f, setF] = useState(empty);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (<>
    <h1>Clients</h1>
    <form className="panel inline" onSubmit={(e) => { e.preventDefault(); act(() => call("/customers", "POST", f)); setF(empty); }}>
      <input required placeholder="Nom" value={f.name} onChange={set("name")} />
      <input required type="email" placeholder="Email" value={f.email} onChange={set("email")} />
      <input placeholder="Entreprise" value={f.company} onChange={set("company")} />
      <button className="btn">Ajouter</button>
    </form>
    <div className="panel"><table><thead><tr><th>Nom</th><th>Email</th><th>Entreprise</th><th /></tr></thead><tbody>
      {customers.map((c) => (<tr key={c.id}><td><b>{c.name}</b></td><td>{c.email}</td><td>{c.company}</td>
        <td><button className="link" onClick={() => confirm("Supprimer ce client et ses demandes ?") && act(() => call(`/customers/${c.id}`, "DELETE"))}>Supprimer</button></td></tr>))}
    </tbody></table></div>
  </>);
}

function Tickets({ tickets, customers, act }) {
  const [sel, setSel] = useState(null);
  const [ai, setAi] = useState(null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(false);
  const [f, setF] = useState({ customer_id: "", subject: "", message: "" });
  const t = tickets.find((x) => x.id === sel);
  const pick = (x) => { setSel(x.id); setAi(x.ai_reply ? { topic: x.topic, priority: x.priority, reply: x.ai_reply } : null); setReply(""); };
  const analyze = async () => {
    setLoading(true);
    await act(async () => setAi(await call(`/tickets/${t.id}/analyze`, "POST")));
    setLoading(false);
  };
  return (<>
    <h1>Demandes</h1>
    <form className="panel inline" onSubmit={(e) => { e.preventDefault(); act(() => call("/tickets", "POST", { ...f, customer_id: +f.customer_id })); setF({ customer_id: "", subject: "", message: "" }); }}>
      <select required value={f.customer_id} onChange={(e) => setF({ ...f, customer_id: e.target.value })}>
        <option value="">Client…</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      <input required placeholder="Objet" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} />
      <input required placeholder="Message du client" value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} />
      <button className="btn">Créer</button>
    </form>
    <div className="split">
      <div className="panel list">{tickets.map((x) => (
        <div key={x.id} className={`row click ${x.id === sel ? "sel" : ""}`} onClick={() => pick(x)}>
          <div><b>{x.subject}</b><div className="muted">{x.customer_name}</div></div>
          <div className="tags"><Badge kind={x.priority === "haute" ? "rose" : "grey"}>{x.priority}</Badge>
            <Badge kind={x.status === "resolue" ? "mint" : x.status === "en_cours" ? "blue" : "yellow"}>{STATUS[x.status]}</Badge></div>
        </div>))}</div>
      <div className="panel detail">{!t ? <p className="muted">Sélectionne une demande.</p> : (<>
        <h2>{t.subject}</h2><p className="muted">{t.customer_name}</p>
        <div className="bubble">{t.message}</div>
        <select value={t.status} onChange={(e) => act(() => call(`/tickets/${t.id}`, "PATCH", { status: e.target.value }))}>
          {Object.entries(STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        <button className="btn" onClick={analyze} disabled={loading}>{loading ? "Analyse…" : "✨ Analyser avec l'IA"}</button>
        {ai && <div className="ai"><div className="tags"><Badge kind="blue">{ai.topic}</Badge><Badge kind={ai.priority === "haute" ? "rose" : "grey"}>{ai.priority}</Badge></div>
          <p>{ai.reply}</p><button className="btn ghost" onClick={() => setReply(ai.reply)}>Insérer la réponse</button></div>}
        <textarea rows="4" placeholder="Votre réponse au client…" value={reply} onChange={(e) => setReply(e.target.value)} />
      </>)}</div>
    </div>
  </>);
}

const INTEREST = { chaud: ["mint", "Chaud"], tiede: ["yellow", "Tiède"], froid: ["grey", "Froid"] };

function Calls({ calls, customers, act }) {
  const [f, setF] = useState({ customer_id: "", notes: "" });
  const [loading, setLoading] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setLoading(true);
    await act(() => call("/calls", "POST", { ...f, customer_id: +f.customer_id }));
    setF({ customer_id: "", notes: "" }); setLoading(false);
  };
  return (<>
    <h1>Appels commerciaux</h1><p className="muted">Colle les notes d'un appel : résumé, intérêt et prochaine action sont proposés.</p>
    <form className="panel detail" onSubmit={submit}>
      <select required value={f.customer_id} onChange={(e) => setF({ ...f, customer_id: e.target.value })}>
        <option value="">Client…</option>{customers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>
      <textarea required rows="4" placeholder="Notes de l'appel…" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
      <button className="btn" disabled={loading}>{loading ? "Analyse…" : "✨ Analyser l'appel"}</button>
    </form>
    {calls.map((k) => (<div className="panel detail" key={k.id}>
      <div className="row"><b>{k.customer_name}</b><Badge kind={INTEREST[k.interest][0]}>{INTEREST[k.interest][1]}</Badge></div>
      <p>{k.summary}</p><div className="bubble"><b>Prochaine action :</b> {k.next_action}</div></div>))}
  </>);
}
