export interface InvoiceItem {
  id?: string; // For client-side keying, might not be in DB JSON as ID
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

export type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'void';

export interface Invoice {
  id: string; // uuid
  user_id: string; // uuid
  invoice_number: string;
  client_name: string;
  client_email?: string | null;
  issue_date: string; // ISO date string (e.g., "2023-10-26")
  due_date: string;   // ISO date string
  total_amount: number;
  status: InvoiceStatus;
  items?: InvoiceItem[] | null;
  notes?: string | null;
  created_at: string; // timestamptz
  updated_at: string; // timestamptz
}

// For creating new invoices, some fields are optional or not yet present
export type NewInvoice = Omit<Invoice, 'id' | 'user_id' | 'created_at' | 'updated_at' | 'status'> & {
  status?: InvoiceStatus; // Status can be optional initially, defaulting to 'draft'
};

// For updating invoices, ID is required, others are partial
export type UpdateInvoice = Partial<Omit<Invoice, 'id' | 'user_id' | 'created_at' | 'updated_at'>> & {
  id: string;
};
