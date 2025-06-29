export interface PayrollEntry {
  id: string; // Client-side generated UUID
  employeeName: string;
  payPeriodStart: string; // ISO date string
  payPeriodEnd: string; // ISO date string
  grossPay: number;
  deductions?: number; // Optional for this basic version
  netPay?: number;     // Optional, could be calculated if gross and deductions are present
  payDate: string; // ISO date string
  notes?: string;
}
