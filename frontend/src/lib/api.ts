const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchScores() {
  const res = await fetch(`${API_BASE}/scores`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch scores');
  return res.json();
}

export async function fetchArticles() {
  const res = await fetch(`${API_BASE}/articles`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch articles');
  return res.json();
}

export async function fetchCorrelation() {
  const res = await fetch(`${API_BASE}/correlation`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch correlation metrics');
  return res.json();
}
