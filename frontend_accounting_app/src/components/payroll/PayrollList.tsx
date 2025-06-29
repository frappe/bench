import { PayrollEntry } from '@/types/payroll';

interface PayrollListProps {
  entries: PayrollEntry[];
  onDeleteEntry?: (id: string) => void; // Optional delete functionality
}

export default function PayrollList({ entries, onDeleteEntry }: PayrollListProps) {
  if (entries.length === 0) {
    return <p>No payroll entries recorded yet.</p>;
  }

  return (
    <div style={{ marginTop: '20px' }}>
      <h4>Recorded Payroll Entries</h4>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {entries.map((entry) => (
          <li key={entry.id} style={{ padding: '10px', border: '1px solid #f0f0f0', marginBottom: '10px', borderRadius: '4px' }}>
            <div>
              <strong>Employee:</strong> {entry.employeeName} <br />
              <strong>Period:</strong> {new Date(entry.payPeriodStart).toLocaleDateString()} - {new Date(entry.payPeriodEnd).toLocaleDateString()} <br />
              <strong>Gross Pay:</strong> ${entry.grossPay.toFixed(2)} | <strong>Pay Date:</strong> {new Date(entry.payDate).toLocaleDateString()}
              {entry.notes && <><br /><em>Notes: {entry.notes}</em></>}
            </div>
            {onDeleteEntry && (
              <button
                onClick={() => onDeleteEntry(entry.id)}
                style={{backgroundColor: 'salmon', color: 'white', border: 'none', borderRadius: '4px', padding: '5px 8px', fontSize: '0.8em', marginTop: '5px'}}>
                Delete
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
