import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const STATUS_OPTIONS = [
  'ALL',
  'DRAFT',
  'ISSUED',
  'PARTIALLY_PAID',
  'PAID',
  'OVERDUE',
  'CANCELLED',
];

const statusLabels = {
  DRAFT: 'Draft',
  ISSUED: 'Issued',
  PARTIALLY_PAID: 'Partially Paid',
  PAID: 'Paid',
  OVERDUE: 'Overdue',
  CANCELLED: 'Cancelled',
};

const formatCurrency = (value) => {
  const num = Number(value || 0);
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(num);
};

const formatDate = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const normalizeList = (data) => (Array.isArray(data) ? data : data?.results || []);

function App() {
  const [invoices, setInvoices] = useState([]);
  const [summary, setSummary] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastSync, setLastSync] = useState('');
  const [filters, setFilters] = useState({
    q: '',
    status: 'ALL',
    min_total: '',
    date_from: '',
    date_to: '',
    overdue: false,
    flagged: false,
  });

  const kpis = useMemo(() => {
    const total = invoices.length;
    const totalValue = invoices.reduce((sum, inv) => sum + Number(inv.total_amount || 0), 0);
    const overdue = invoices.filter((inv) => inv.is_overdue).length;
    const flagged = invoices.filter((inv) => inv.is_flagged).length;
    return { total, totalValue, overdue, flagged };
  }, [invoices]);

  const buildQuery = () => {
    const params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.status && filters.status !== 'ALL') params.set('status', filters.status);
    if (filters.min_total) params.set('min_total', filters.min_total);
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.overdue) params.set('overdue', 'true');
    if (filters.flagged) params.set('flagged', 'true');
    const query = params.toString();
    return query ? `?${query}` : '';
  };

  const fetchInvoices = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/invoices/${buildQuery()}`);
      setInvoices(normalizeList(res.data));
      setLastSync(new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }));
    } catch (e) {
      setError('Failed to fetch invoices. Is the API running on port 8000?');
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchSuggested = async () => {
    setError('');
    try {
      const res = await axios.get(`${API_BASE}/ai-suggest/?min_total=${filters.min_total || 10000}`);
      setSuggestions(normalizeList(res.data));
    } catch (e) {
      setError('Failed to fetch suggested invoices.');
      setSuggestions([]);
    }
  };

  const fetchSummary = async () => {
    setError('');
    try {
      const res = await axios.get(`${API_BASE}/summary/`);
      setSummary(normalizeList(res.data));
    } catch (e) {
      setError('Failed to fetch summary.');
      setSummary([]);
    }
  };

  const refreshAll = async () => {
    await Promise.all([fetchInvoices(), fetchSummary(), fetchSuggested()]);
  };

  const toggleFlag = async (invoice) => {
    const nextFlag = !invoice.is_flagged;
    setInvoices((prev) =>
      prev.map((item) => (item.id === invoice.id ? { ...item, is_flagged: nextFlag } : item))
    );
    try {
      await axios.patch(`${API_BASE}/invoices/${invoice.id}/`, { is_flagged: nextFlag });
    } catch (e) {
      setError('Failed to update flag status.');
      setInvoices((prev) =>
        prev.map((item) => (item.id === invoice.id ? { ...item, is_flagged: invoice.is_flagged } : item))
      );
    }
  };

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-card">
          <p className="eyebrow">Invoice Intelligence</p>
          <h1 className="hero-title">Real-time visibility for every invoice.</h1>
          <p className="hero-subtitle">
            Track airline invoices, surface exceptions, and keep payment risk visible with
            smarter signals.
          </p>
          <div className="hero-actions">
            <button className="btn primary" onClick={fetchInvoices} disabled={loading}>
              {loading ? 'Syncing...' : 'Sync Invoices'}
            </button>
            <button className="btn ghost" onClick={refreshAll} disabled={loading}>
              Refresh All
            </button>
          </div>
          <div className="hero-meta">
            <span>API base: {API_BASE}</span>
            <span>Last sync: {lastSync || '-'}</span>
          </div>
        </div>
        <div className="hero-card hero-kpis">
          <div className="kpi">
            <span className="kpi-label">Total invoices</span>
            <span className="kpi-value">{kpis.total}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Total value</span>
            <span className="kpi-value">{formatCurrency(kpis.totalValue)}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Overdue</span>
            <span className="kpi-value warning">{kpis.overdue}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">Flagged</span>
            <span className="kpi-value accent">{kpis.flagged}</span>
          </div>
        </div>
      </header>

      {error && <div className="alert">{error}</div>}

      <section className="grid">
        <div className="panel filters">
          <h2>Filters</h2>
          <div className="field">
            <label>Search</label>
            <input
              type="text"
              value={filters.q}
              placeholder="Invoice no, vendor, airline, GSTIN"
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              {STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {statusLabels[status] || 'All'}
                </option>
              ))}
            </select>
          </div>
          <div className="field row">
            <div>
              <label>From</label>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              />
            </div>
            <div>
              <label>To</label>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              />
            </div>
          </div>
          <div className="field row">
            <div>
              <label>Min total</label>
              <input
                type="number"
                value={filters.min_total}
                placeholder="10000"
                onChange={(e) => setFilters({ ...filters, min_total: e.target.value })}
              />
            </div>
            <div className="toggle">
              <label>Overdue only</label>
              <input
                type="checkbox"
                checked={filters.overdue}
                onChange={(e) => setFilters({ ...filters, overdue: e.target.checked })}
              />
            </div>
            <div className="toggle">
              <label>Flagged only</label>
              <input
                type="checkbox"
                checked={filters.flagged}
                onChange={(e) => setFilters({ ...filters, flagged: e.target.checked })}
              />
            </div>
          </div>
          <div className="filter-actions">
            <button className="btn primary" onClick={fetchInvoices} disabled={loading}>
              Apply Filters
            </button>
            <button
              className="btn ghost"
              onClick={() =>
                setFilters({
                  q: '',
                  status: 'ALL',
                  min_total: '',
                  date_from: '',
                  date_to: '',
                  overdue: false,
                  flagged: false,
                })
              }
            >
              Reset
            </button>
          </div>
        </div>

        <div className="panel summary">
          <div className="panel-header">
            <h2>Airline Summary</h2>
            <button className="btn ghost" onClick={fetchSummary} disabled={loading}>
              Refresh
            </button>
          </div>
          {summary.length === 0 ? (
            <p className="muted">No summary data yet.</p>
          ) : (
            <div className="summary-grid">
              {summary.slice(0, 6).map((item) => (
                <div className="summary-card" key={item.airline}>
                  <h3>{item.airline}</h3>
                  <p>{formatCurrency(item.total_amount)}</p>
                  <span>{item.invoice_count} invoices</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel signals">
          <div className="panel-header">
            <h2>Signals</h2>
            <button className="btn ghost" onClick={fetchSuggested} disabled={loading}>
              Scan
            </button>
          </div>
          {suggestions.length === 0 ? (
            <p className="muted">No signals to review.</p>
          ) : (
            <div className="signals-list">
              {suggestions.slice(0, 6).map((item) => (
                <div className="signal-card" key={item.id}>
                  <div>
                    <h3>{item.invoice_no}</h3>
                    <p>{item.airline || 'Unknown airline'}</p>
                  </div>
                  <div className="signal-meta">
                    <span>{formatCurrency(item.total_amount)}</span>
                    <div className="signal-tags">
                      {(item.signals || []).map((signal) => (
                        <span className={`chip ${signal}`} key={signal}>
                          {signal.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="panel table-panel">
        <div className="panel-header">
          <h2>Invoices</h2>
          <button className="btn ghost" onClick={fetchInvoices} disabled={loading}>
            Refresh List
          </button>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Invoice</th>
                <th>Issue date</th>
                <th>Airline</th>
                <th>Vendor</th>
                <th>Total</th>
                <th>Status</th>
                <th>GSTIN</th>
                <th>Flag</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length === 0 ? (
                <tr>
                  <td colSpan="8" className="empty">
                    No invoices yet. Sync to load data.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <div className="cell-title">{inv.invoice_no}</div>
                      <div className="cell-sub">{formatDate(inv.due_date)}</div>
                    </td>
                    <td>{formatDate(inv.issue_date)}</td>
                    <td>{inv.airline || '-'}</td>
                    <td>{inv.vendor_name || '-'}</td>
                    <td>{formatCurrency(inv.total_amount)}</td>
                    <td>
                      <span className={`badge ${inv.status?.toLowerCase() || ''}`}>
                        {statusLabels[inv.status] || inv.status || '-'}
                      </span>
                      {inv.is_overdue && <span className="badge overdue">Overdue</span>}
                    </td>
                    <td>{inv.gstin || '-'}</td>
                    <td>
                      <label className="switch">
                        <input
                          type="checkbox"
                          checked={!!inv.is_flagged}
                          onChange={() => toggleFlag(inv)}
                        />
                        <span />
                      </label>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default App;
