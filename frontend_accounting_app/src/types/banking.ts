export interface BankTransaction {
  id: string; // Client-side generated for keying, or from DB if persisted
  date: string; // ISO date string
  description: string;
  amount: number; // Positive for deposits, negative for withdrawals
  category?: string; // To be assigned by user or AI
  status?: 'unreconciled' | 'reconciled' | 'pending_categorization'; // For later use
}

// Expected CSV structure (example)
// Date,Description,Amount
// 2023-01-15,Initial Deposit,1000.00
// 2023-01-16,Office Supplies,-50.25
// 2023-01-17,Client Payment,250.50
