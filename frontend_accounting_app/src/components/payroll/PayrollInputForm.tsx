import { useState } from 'react';
import { PayrollEntry } from '@/types/payroll';
import { v4 as uuidv4 } from 'uuid';

interface PayrollInputFormProps {
  onAddEntry: (entry: PayrollEntry) => void;
  userId: string | undefined;
}

export default function PayrollInputForm({ onAddEntry, userId }: PayrollInputFormProps) {
  const [employeeName, setEmployeeName] = useState('');
  const [payPeriodStart, setPayPeriodStart] = useState('');
  const [payPeriodEnd, setPayPeriodEnd] = useState('');
  const [grossPay, setGrossPay] = useState<number | ''>('');
  const [payDate, setPayDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');

  const [loading, setLoading] = useState(false); // For future async operations
  const [message, setMessage] = useState('');

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userId) {
      setMessage('User not identified.');
      return;
    }
    setLoading(true); // Simulate async for now
    setMessage('');

    if (!employeeName || !payPeriodStart || !payPeriodEnd || grossPay === '' || !payDate) {
        setMessage('Error: Please fill in all required fields (Employee Name, Pay Period, Gross Pay, Pay Date).');
        setLoading(false);
        return;
    }

    const newEntry: PayrollEntry = {
      id: uuidv4(),
      employeeName,
      payPeriodStart,
      payPeriodEnd,
      grossPay: Number(grossPay),
      payDate,
      notes,
      // Deductions and NetPay can be added later
    };

    try {
      onAddEntry(newEntry);
      setMessage('Payroll entry added successfully (client-side).');
      // Reset form
      setEmployeeName('');
      setPayPeriodStart('');
      setPayPeriodEnd('');
      setGrossPay('');
      setPayDate(new Date().toISOString().split('T')[0]);
      setNotes('');
    } catch (error: any) {
      console.error('Error adding payroll entry:', error);
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!userId) {
    return <p>Please sign in to manage payroll data.</p>;
  }

  return (
    <form onSubmit={handleSubmit} style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px', marginBottom: '20px' }}>
      <h3>Add New Payroll Entry (Manual)</h3>
      <div>
        <label>Employee Name: <input type="text" value={employeeName} onChange={(e) => setEmployeeName(e.target.value)} required /></label>
      </div>
      <div>
        <label>Pay Period Start: <input type="date" value={payPeriodStart} onChange={(e) => setPayPeriodStart(e.target.value)} required /></label>
      </div>
      <div>
        <label>Pay Period End: <input type="date" value={payPeriodEnd} onChange={(e) => setPayPeriodEnd(e.target.value)} required /></label>
      </div>
      <div>
        <label>Gross Pay: <input type="number" value={grossPay} onChange={(e) => setGrossPay(Number(e.target.value))} min="0" step="0.01" required /></label>
      </div>
      <div>
        <label>Pay Date: <input type="date" value={payDate} onChange={(e) => setPayDate(e.target.value)} required /></label>
      </div>
       <div>
        <label>Notes (Optional): <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} style={{width: '100%', marginTop: '5px'}} /></label>
      </div>

      <button type="submit" disabled={loading} style={{marginTop: '10px'}}>
        {loading ? 'Adding...' : 'Add Payroll Entry'}
      </button>
      {message && <p style={{ color: message.startsWith('Error:') ? 'red' : 'green', marginTop: '10px' }}>{message}</p>}
    </form>
  );
}
