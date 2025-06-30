import { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Expense, NewExpense, COMMON_EXPENSE_CATEGORIES } from '@/types/expense'; // Assuming types are in @/types

interface ExpenseFormProps {
  onExpenseCreated: (newExpense: Expense)<strong> => </strong>void;
  userId: string | undefined;
}

export default function ExpenseForm({ onExpenseCreated, userId }: ExpenseFormProps) {
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().split('T')[0]);
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [amount, setAmount] = useState<number | ''>('');
  const [notes, setNotes] = useState('');
  // Optional: receipt_url would need file upload handling, which is more complex for this step.

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userId) {
      setMessage('User not identified. Please sign in.');
      return;
    }
    if (amount === '' || amount <= 0) {
      setMessage('Error: Amount must be a positive number.');
      return;
    }
    if (!description.trim() || !category.trim()) {
        setMessage('Error: Description and Category are required.');
        return;
    }

    setLoading(true);
    setMessage('');

    const newExpenseData: NewExpense = {
      expense_date: expenseDate,
      description,
      category,
      amount: Number(amount),
      notes,
      // receipt_url: undefined, // Add if implementing file uploads
    };

    try {
      const { data, error } = await supabase
        .from('expenses')
        .insert([{ ...newExpenseData, user_id: userId }])
        .select()
        .single();

      if (error) throw error;
      if (data) {
        setMessage('Expense created successfully!');
        onExpenseCreated(data as Expense);
        // Reset form
        setExpenseDate(new Date().toISOString().split('T')[0]);
        setDescription('');
        setCategory('');
        setAmount('');
        setNotes('');
      }
    } catch (error: any) {
      console.error('Error creating expense:', error);
      setMessage(`Error creating expense: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!userId) {
    return <p>Please sign in to add expenses.</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 border border-gray-200 rounded-lg shadow space-y-4 mb-6 bg-white">
      <h3 className="text-lg font-semibold text-gray-800">Add New Expense</h3>

      <div>
        <label htmlFor="expenseDate" className="block text-sm font-medium text-gray-700">Date:</label>
        <input
          id="expenseDate" type="date" value={expenseDate}
          onChange={(e) => setExpenseDate(e.target.value)} required
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700">Description:</label>
        <input
          id="description" type="text" value={description}
          onChange={(e) => setDescription(e.target.value)} required
          placeholder="e.g., Office lunch, Software subscription"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div>
        <label htmlFor="category" className="block text-sm font-medium text-gray-700">Category:</label>
        <input
          id="category" type="text" value={category}
          onChange={(e) => setCategory(e.target.value)} required
          list="expenseCategories"
          placeholder="e.g., Meals, Software"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
        <datalist id="expenseCategories">
          {COMMON_EXPENSE_CATEGORIES.map(cat => <option key={cat} value={cat} />)}
        </datalist>
      </div>

      <div>
        <label htmlFor="amount" className="block text-sm font-medium text-gray-700">Amount:</label>
        <input
          id="amount" type="number" value={amount}
          onChange={(e) => setAmount(e.target.value === '' ? '' : Number(e.target.value))}
          min="0.01" step="0.01" required
          placeholder="0.00"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div>
        <label htmlFor="notes" className="block text-sm font-medium text-gray-700">Notes (Optional):</label>
        <textarea
          id="notes" value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <button
        type="submit" disabled={loading}
        className="w-full sm:w-auto px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
      >
        {loading ? 'Adding Expense...' : 'Add Expense'}
      </button>

      {message && <p className={`mt-2 text-sm ${message.startsWith('Error:') ? 'text-red-600' : 'text-green-600'}`}>{message}</p>}
    </form>
  );
}
