import { useState } from 'react';
import { Expense } from '@/types/expense';
import ExpenseForm from './ExpenseForm';
import ExpenseList from './ExpenseList';

interface ExpensesPageProps {
  userId: string | undefined;
}

export default function ExpensesPage({ userId }: ExpensesPageProps) {
  // This state is used as a 'key' to trigger re-fetch in ExpenseList
  // when a new expense is created. Incrementing it will change the prop,
  // causing useEffect in ExpenseList to run again.
  const [listRefreshKey, setListRefreshKey] = useState(0);

  const handleExpenseCreated = (newExpense: Expense) => {
    // newExpense is available here if needed for any immediate UI update,
    // but ExpenseList will re-fetch the whole list.
    console.log('New expense created on page:', newExpense);
    setListRefreshKey(prevKey => prevKey + 1); // Trigger list refresh
  };

  if (!userId) {
    // This check might be redundant if App.tsx already gates access,
    // but good for component isolation or direct routing scenarios.
    return <p className="p-4 text-gray-600">Please sign in to manage your expenses.</p>;
  }

  return (
    <div className="mt-6"> {/* Changed from py-6 for less top padding if App has it */}
      <header className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Manage Expenses</h2>
        <p className="text-sm text-gray-600">Track your business spending here.</p>
      </header>

      <ExpenseForm
        userId={userId}
        onExpenseCreated={handleExpenseCreated}
      />

      <ExpenseList
        userId={userId}
        refreshKey={listRefreshKey}
      />
    </div>
  );
}
