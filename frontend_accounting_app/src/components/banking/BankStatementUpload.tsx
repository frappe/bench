import { useState } from 'react';
import { BankTransaction } from '@/types/banking';
import { v4 as uuidv4 } from 'uuid'; // For generating client-side IDs

interface BankStatementUploadProps {
  userId: string | undefined; // May be used later for saving/associating transactions
}

// Basic CSV parser
// Assumes:
// - Comma-separated values.
// - First row is header (Date,Description,Amount).
// - No complex CSV features like quoted fields containing commas for now.
function parseBankStatementCSV(csvString: string): BankTransaction[] {
  const transactions: BankTransaction[] = [];
  const lines = csvString.trim().split('\n');

  if (lines.length < 2) { // Needs at least header + 1 data row
    throw new Error("CSV must have a header row and at least one data row.");
  }

  const header = lines[0].split(',').map(h => h.trim().toLowerCase());
  const dateIndex = header.indexOf('date');
  const descriptionIndex = header.indexOf('description');
  const amountIndex = header.indexOf('amount');

  if (dateIndex === -1 || descriptionIndex === -1 || amountIndex === -1) {
    throw new Error("CSV header must contain 'Date', 'Description', and 'Amount' columns.");
  }

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',');
    if (values.length < Math.max(dateIndex, descriptionIndex, amountIndex) + 1) {
        console.warn(`Skipping malformed row: ${lines[i]}`);
        continue;
    }
    try {
      const dateStr = values[dateIndex].trim();
      // Attempt to parse various common date formats or just store as string if robust parsing is out of scope
      // For simplicity, we'll assume it's a parseable date string or already ISO-like.
      // A real app would use a date parsing library.
      const date = new Date(dateStr).toISOString().split('T')[0]; // Basic conversion

      const description = values[descriptionIndex].trim();
      const amount = parseFloat(values[amountIndex].trim());

      if (isNaN(amount)) {
        console.warn(`Skipping row with invalid amount: ${lines[i]}`);
        continue;
      }

      transactions.push({
        id: uuidv4(), // Client-side ID
        date: date,
        description: description,
        amount: amount,
        status: 'pending_categorization',
      });
    } catch (parseError) {
        console.warn(`Error parsing row, skipping: ${lines[i]}`, parseError);
    }
  }
  return transactions;
}


export default function BankStatementUpload({ userId }: BankStatementUploadProps) {
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setTransactions([]);
      setError(null);
      setFileName('');
      return;
    }

    setLoading(true);
    setError(null);
    setFileName(file.name);

    try {
      const fileContent = await file.text();
      const parsedTransactions = parseBankStatementCSV(fileContent);
      setTransactions(parsedTransactions);
    } catch (err: any) {
      console.error("Error processing CSV file:", err);
      setError(`Failed to process CSV: ${err.message}`);
      setTransactions([]);
    } finally {
        setLoading(false);
    }
  };

  const handleCategorize = (transactionId: string) => {
    // Placeholder for AI categorization logic
    console.log(`AI Categorization triggered for transaction ID: ${transactionId}`);
    alert(`AI Categorization for transaction ${transactionId} (not yet implemented).`);
    // Future: update transaction category in state and potentially in DB
  };

  if (!userId) {
    return <p>Please sign in to manage bank transactions.</p>;
  }

  return (
    <div style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px', marginTop: '20px' }}>
      <h3>Upload Bank Statement (CSV)</h3>
      <p style={{fontSize: '0.9em', color: '#555'}}>Expected CSV columns: Date, Description, Amount</p>
      <input type="file" accept=".csv" onChange={handleFileChange} disabled={loading} />
      {fileName && <p>Selected file: {fileName}</p>}
      {loading && <p>Processing file...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {transactions.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h4>Uploaded Transactions ({transactions.length})</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {transactions.map((tx) => (
              <li key={tx.id} style={{ padding: '10px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>{tx.date}</strong> - {tx.description} <br />
                  Amount: <span style={{ color: tx.amount >= 0 ? 'green' : 'red' }}>{tx.amount.toFixed(2)}</span>
                  {tx.category && <span> | Category: {tx.category}</span>}
                </div>
                <button onClick={() => handleCategorize(tx.id)} style={{padding: '5px 8px', fontSize: '0.8em'}}>
                  Categorize (Auto)
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
