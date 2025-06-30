import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Invoice } from '@/types/invoice'; // Keep this
import { Expense } from '@/types/expense'; // Add this

interface ProfitAndLossReportProps {
  userId: string | undefined;
  // Optional: Add date range filters later
  // startDate?: string;
  // endDate?: string;
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
      // Fetch paid invoices for revenue
      const { data: invoices, error: invoicesError } = await supabase
        .from('invoices')
        .select('total_amount, status')
        .eq('user_id', userId)
        .eq('status', 'paid');
        // TODO: Add date range filtering if startDate/endDate props are used

      if (invoicesError) throw invoicesError;
      const totalRevenue = invoices?.reduce((sum, invoice) => sum + invoice.total_amount, 0) || 0;

      // Fetch expenses
      const { data: expenses, error: expensesError } = await supabase
        .from('expenses')
        .select('amount')
        .eq('user_id', userId);
        // TODO: Add date range filtering if startDate/endDate props are used

      if (expensesError) throw expensesError;
      const totalExpenses = expenses?.reduce((sum, expense) => sum + expense.amount, 0) || 0;

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
    <div className="p-4 border border-gray-200 rounded-lg shadow space-y-3 mt-6 bg-white">
      <h3 className="text-lg font-semibold text-gray-800">Profit & Loss Statement</h3>
      {error && <p className="text-sm text-red-600">Error: {error}</p>}

      <div className="space-y-1">
        <p className="text-sm text-gray-700">
          <strong>Total Revenue:</strong>
          <span className="font-semibold text-green-600 ml-2">${pnlData.totalRevenue.toFixed(2)}</span>
        </p>
        <p className="text-sm text-gray-700">
          <strong>Total Expenses:</strong>
          <span className="font-semibold text-red-600 ml-2">${pnlData.totalExpenses.toFixed(2)}</span>
        </p>
        <hr className="my-1" />
        <p className="text-sm text-gray-900">
          <strong>Net Profit:</strong>
          <span className={`font-bold ml-2 ${pnlData.netProfit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            ${pnlData.netProfit.toFixed(2)}
          </span>
        </p>
      </div>

      <button
        onClick={fetchReportData}
        disabled={loading}
        className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {loading ? 'Refreshing...' : 'Refresh Report'}
      </button>
      {lastRefreshed && <p className="text-xs text-gray-500 mt-1">Last refreshed: {lastRefreshed}</p>}
    </div>
  );
}
