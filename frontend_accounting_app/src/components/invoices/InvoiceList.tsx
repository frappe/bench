import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Invoice, InvoiceStatus } from '@/types/invoice'; // Import InvoiceStatus

interface InvoiceListProps {
  userId: string | undefined;
  onInvoiceSelect?: (invoice: Invoice) => void; // For future view/edit
  onInvoiceCountChange: (count: number) => void;
}

export default function InvoiceList({ userId, onInvoiceSelect, onInvoiceCountChange }: InvoiceListProps) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (userId) {
      fetchInvoices();
    } else {
      setLoading(false);
      setInvoices([]); // Clear invoices if user logs out
    }
  }, [userId]);

  const fetchInvoices = async () => {
    if (!userId) return;
    setLoading(true);
    setError(null);
    try {
      const { data, error, count } = await supabase
        .from('invoices')
        .select('*', { count: 'exact' }) // Request count along with data
        .eq('user_id', userId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      if (data) {
        setInvoices(data);
        onInvoiceCountChange(count || 0); // Update parent with the count
      } else {
        onInvoiceCountChange(0);
      }
    } catch (err: any) {
      console.error('Error fetching invoices:', err);
      setError(err.message);
      onInvoiceCountChange(0); // Reset count on error
    } finally {
      setLoading(false);
    }
  };

  // Expose fetchInvoices to be called from parent if needed (e.g., after creating an invoice)
  // This is implicitly handled if onInvoiceCreated in parent triggers a re-render or state change
  // that causes this component to re-evaluate its useEffect, or if we pass a refresh trigger.
  // For now, the list will be updated when a new invoice is added via the onInvoiceCreated callback in the parent
  // which should then update the currentInvoiceCount, causing a re-render of the form and potentially the list.

  const handleDelete = async (invoiceId: string) => {
    if (!window.confirm('Are you sure you want to delete this invoice?')) return;
    try {
      const { error } = await supabase.from('invoices').delete().eq('id', invoiceId);
      if (error) throw error;
      // Refresh list after delete
      fetchInvoices();
    } catch (err: any) {
      console.error('Error deleting invoice:', err);
      setError(`Failed to delete invoice: ${err.message}`);
    }
  };

  const handleTogglePaidStatus = async (invoice: Invoice) => {
    const newStatus: InvoiceStatus = invoice.status === 'paid' ? 'sent' : 'paid'; // Toggle between 'sent' and 'paid'
    try {
      const { data, error } = await supabase
        .from('invoices')
        .update({ status: newStatus, updated_at: new Date().toISOString() })
        .eq('id', invoice.id)
        .select()
        .single();

      if (error) throw error;

      // Update local state for immediate UI feedback
      setInvoices(prevInvoices =>
        prevInvoices.map(inv => inv.id === invoice.id ? data as Invoice : inv)
      );
    } catch (err: any) {
      console.error('Error updating invoice status:', err);
      // Potentially set an error message to display to the user
      setError(`Failed to update status: ${err.message}`);
    }
  };


  if (loading) return <p>Loading invoices...</p>;
  if (error) return <p style={{ color: 'red' }}>Error loading invoices: {error}</p>;
  if (!userId) return <p>Please sign in to view invoices.</p>;

  return (
    <div style={{ marginTop: '20px' }}>
      <h3>Your Invoices ({invoices.length})</h3>
      {invoices.length === 0 ? (
        <p>No invoices found. Create one above!</p>
      ) : (
        <ul className="space-y-3"> {/* Using Tailwind for spacing between list items */}
          {invoices.map((invoice) => (
            // Using Tailwind for styling list items, flex layout, and responsiveness
            <li
              key={invoice.id}
              className="p-3 bg-white border border-gray-200 rounded-md shadow-sm flex flex-col sm:flex-row justify-between sm:items-center"
            >
              <div className="mb-2 sm:mb-0"> {/* Margin bottom on small screens only */}
                <strong className="text-sm font-medium text-gray-900">{invoice.invoice_number}</strong> - <span className="text-sm text-gray-700">{invoice.client_name}</span> <br />
                <span className="text-xs text-gray-600">Amount: ${invoice.total_amount.toFixed(2)} | Status: {invoice.status}</span> <br />
                <span className="text-xs text-gray-600">Due: {new Date(invoice.due_date).toLocaleDateString()}</span>
              </div>
              {/* Responsive button group: flex-col on small screens (default), sm:flex-row on small breakpoint and up */}
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 self-start sm:self-center"> {/* Buttons align start on col, center on row */}
                <button
                  onClick={() => handleTogglePaidStatus(invoice)}
                  className={`px-2.5 py-1.5 text-xs font-semibold rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 w-full sm:w-auto transition-colors
                    ${invoice.status === 'paid' ? 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500'
                                              : 'bg-yellow-400 hover:bg-yellow-500 text-gray-800 focus:ring-yellow-400'}`}
                >
                  {invoice.status === 'paid' ? 'Mark Unpaid' : 'Mark Paid'}
                </button>
                {onInvoiceSelect &&
                  <button
                    onClick={() => onInvoiceSelect(invoice)}
                    className="px-2.5 py-1.5 text-xs font-semibold text-gray-700 bg-gray-200 rounded-md shadow-sm hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 w-full sm:w-auto transition-colors"
                  >
                    View/Edit
                  </button>
                }
                <button
                  onClick={() => handleDelete(invoice.id)}
                  className="px-2.5 py-1.5 text-xs font-semibold text-white bg-red-600 rounded-md shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 w-full sm:w-auto transition-colors"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
