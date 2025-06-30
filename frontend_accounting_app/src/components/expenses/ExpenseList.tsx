import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Expense } from '@/types/expense';

interface ExpenseListProps {
  userId: string | undefined;
  // Used to trigger a refresh if an expense is added/deleted outside this component's direct actions
  // For instance, if the form is part of the same parent, the parent can increment this key.
  refreshKey?: number;
}

export default function ExpenseList({ userId, refreshKey }: ExpenseListProps) {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchExpenses = useCallback(async () => {
    if (!userId) {
      setExpenses([]); // Clear if no user
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data, error: fetchError } = await supabase
        .from('expenses')
        .select('*')
        .eq('user_id', userId)
        .order('expense_date', { ascending: false })
        .order('created_at', { ascending: false });

      if (fetchError) throw fetchError;
      setExpenses(data || []);
    } catch (err: any) {
      console.error('Error fetching expenses:', err);
      setError(err.message);
      setExpenses([]); // Clear on error
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchExpenses();
  }, [fetchExpenses, refreshKey]); // Re-fetch if userId changes or refreshKey changes

  const handleDelete = async (expenseId: string) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) return;
    try {
      const { error: deleteError } = await supabase.from('expenses').delete().eq('id', expenseId);
      if (deleteError) throw deleteError;
      // Refresh list after delete by calling fetchExpenses directly
      // or by relying on parent to change refreshKey if that pattern is preferred.
      // Calling directly is simpler here.
      fetchExpenses();
    } catch (err: any) {
      console.error('Error deleting expense:', err);
      setError(`Failed to delete expense: ${err.message}`);
    }
  };

  if (loading) return <p className="text-gray-600">Loading expenses...</p>;
  if (error) return <p className="text-red-600">Error loading expenses: {error}</p>;
  if (!userId) return null; // Or a message like "Please sign in" if not handled by parent

  return (
    <div className="mt-6 bg-white p-4 shadow rounded-lg">
      <h3 className="text-lg font-semibold text-gray-800 mb-3">Your Expenses</h3>
      {expenses.length === 0 ? (
        <p className="text-gray-500">No expenses recorded yet. Add one using the form above!</p>
      ) : (
        <ul className="space-y-3">
          {expenses.map((expense) => (
            <li
              key={expense.id}
              className="p-3 border border-gray-200 rounded-md flex flex-col sm:flex-row justify-between sm:items-center hover:bg-gray-50 transition-colors"
            >
              <div className="mb-2 sm:mb-0 flex-grow">
                <div className="flex justify-between items-baseline">
                    <strong className="text-sm font-medium text-gray-900">{expense.description}</strong>
                    <span className="text-sm font-semibold text-red-600">-${expense.amount.toFixed(2)}</span>
                </div>
                <div className="text-xs text-gray-600">
                  <span>{new Date(expense.expense_date).toLocaleDateString()}</span> | <span>Category: {expense.category}</span>
                </div>
                {expense.notes && <p className="text-xs text-gray-500 mt-1 italic">Notes: {expense.notes}</p>}
              </div>
              <div className="mt-2 sm:mt-0 sm:ml-4 flex-shrink-0">
                <button
                  onClick={() => handleDelete(expense.id)}
                  className="px-2.5 py-1.5 text-xs font-semibold text-white bg-red-600 rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
