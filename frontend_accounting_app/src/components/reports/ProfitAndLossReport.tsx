import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Invoice } from '@/types/invoice';

interface ProfitAndLossReportProps {
  userId: string | undefined;
}

interface PNLData {
  totalRevenue: number;
  totalExpenses: number;
  netProfit: number;
}

export default function ProfitAndLossReport({ userId }: ProfitAndLossReportProps) {
  const [pnlData, setPnlData] = useState<PNLData>({ totalRevenue: 0, totalExpenses: 0, netProfit: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');

  const fetchReportData = useCallback(async () => {
    if (!userId) {
      setError("User ID is not available.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const { data: invoices, error: invoicesError } = await supabase
        .from('invoices')
        .select('total_amount, status')
        .eq('user_id', userId)
        .eq('status', 'paid');

      if (invoicesError) throw invoicesError;

      const totalRevenue = invoices.reduce((sum, invoice) => sum + invoice.total_amount, 0);
      const totalExpenses = 0; // Placeholder for now
      const netProfit = totalRevenue - totalExpenses;

      setPnlData({ totalRevenue, totalExpenses, netProfit });
      setLastRefreshed(new Date().toLocaleTimeString());

    } catch (err: any) {
      console.error('Error fetching P&L data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  if (!userId) {
    return <p>Please sign in to view reports.</p>;
  }

  if (loading) return <p>Loading P&L report...</p>;


  return (
    <div style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px', marginTop: '20px' }}>
      <h3>Profit & Loss Statement</h3>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      <p><strong>Total Revenue:</strong> ${pnlData.totalRevenue.toFixed(2)}</p>
      <p><strong>Total Expenses:</strong> ${pnlData.totalExpenses.toFixed(2)} <em>(Note: Expense tracking not yet implemented)</em></p>
      <p><strong>Net Profit:</strong> ${pnlData.netProfit.toFixed(2)}</p>
      <button onClick={fetchReportData} disabled={loading} style={{marginTop: '10px'}}>
        {loading ? 'Refreshing...' : 'Refresh Report'}
      </button>
      {lastRefreshed && <p style={{fontSize: '0.8em', color: '#777', marginTop: '5px'}}>Last refreshed: {lastRefreshed}</p>}
    </div>
  );
}
