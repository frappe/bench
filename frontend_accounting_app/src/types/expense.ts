export interface Expense {
  id: string; // uuid
  user_id: string; // uuid
  expense_date: string; // ISO date string (e.g., "2023-10-27")
  description: string;
  category: string;
  amount: number;
  receipt_url?: string | null;
  notes?: string | null;
  created_at: string; // timestamptz
  updated_at: string; // timestamptz
}

// For creating new expenses, some fields are optional or not yet present
export type NewExpense = Omit<Expense, 'id' | 'user_id' | 'created_at' | 'updated_at'>;

// For updating expenses, ID is required, others are partial
export type UpdateExpense = Partial<Omit<Expense, 'id' | 'user_id' | 'created_at' | 'updated_at'>> & {
  id: string;
};

// Example basic expense categories - can be expanded or managed dynamically later
export const COMMON_EXPENSE_CATEGORIES = [
  "Office Supplies",
  "Software & Subscriptions",
  "Utilities (Electricity, Water, Internet)",
  "Rent & Lease",
  "Meals & Entertainment",
  "Travel (Flights, Accommodation, Mileage)",
  "Marketing & Advertising",
  "Professional Fees (Legal, Accounting)",
  "Bank Fees",
  "Repairs & Maintenance",
  "Salaries & Wages", // Though full payroll is separate, direct expenses can be here
  "Other",
];
