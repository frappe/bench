import { useState, useEffect } from 'react';
import { PayrollEntry } from '@/types/payroll';
import PayrollInputForm from './PayrollInputForm';
import PayrollList from './PayrollList';

interface PayrollPageProps {
  userId: string | undefined;
}

const LOCAL_STORAGE_KEY_PAYROLL = 'manualPayrollEntries';

export default function PayrollPage({ userId }: PayrollPageProps) {
  const [payrollEntries, setPayrollEntries] = useState<PayrollEntry[]>(() => {
    // Load entries from local storage on initial render
    if (typeof window !== 'undefined') {
        const savedEntries = localStorage.getItem(LOCAL_STORAGE_KEY_PAYROLL);
        return savedEntries ? JSON.parse(savedEntries) : [];
    }
    return [];
  });

  // Save entries to local storage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
        localStorage.setItem(LOCAL_STORAGE_KEY_PAYROLL, JSON.stringify(payrollEntries));
    }
  }, [payrollEntries]);


  const handleAddPayrollEntry = (newEntry: PayrollEntry) => {
    setPayrollEntries(prevEntries => [newEntry, ...prevEntries]);
  };

  const handleDeletePayrollEntry = (id: string) => {
    if (window.confirm('Are you sure you want to delete this payroll entry? (This is client-side only)')) {
        setPayrollEntries(prevEntries => prevEntries.filter(entry => entry.id !== id));
    }
  };

  if (!userId) {
    // This check might be redundant if App.tsx already gates access, but good for component isolation
    return <p>Please sign in to access the payroll section.</p>;
  }

  return (
    <div style={{ marginTop: '20px' }}>
      <h2>Manual Payroll Input</h2>
      <p style={{fontSize: '0.9em', color: '#555', marginBottom: '15px'}}>
        This section allows for manual entry of payroll data. Data is stored in your browser&apos;s local storage and is not persisted to the server in this version.
      </p>
      <PayrollInputForm userId={userId} onAddEntry={handleAddPayrollEntry} />
      <PayrollList entries={payrollEntries} onDeleteEntry={handleDeletePayrollEntry} />
    </div>
  );
}
