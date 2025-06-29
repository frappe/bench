import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Invoice, NewInvoice, InvoiceStatus } from '@/types/invoice'; // Assuming types are in @/types

interface InvoiceFormProps {
  onInvoiceCreated: (newInvoice: Invoice)<strong> => </strong>void;
  userId: string | undefined;
  currentInvoiceCount: number;
}

const FREE_TIER_INVOICE_LIMIT = 100;

export default function InvoiceForm({ onInvoiceCreated, userId, currentInvoiceCount }: InvoiceFormProps) {
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [issueDate, setIssueDate] = useState(new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState('');
  const [totalAmount, setTotalAmount] = useState<number | ''>('');
  // Basic item handling for now - can be expanded
  const [itemDescription, setItemDescription] = useState('Service/Product');
  const [itemQuantity, setItemQuantity] = useState<number | ''>(1);
  const [itemUnitPrice, setItemUnitPrice] = useState<number | ''>('');

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [canCreateMore, setCanCreateMore] = useState(true);

  useEffect(() => {
    if (currentInvoiceCount >= FREE_TIER_INVOICE_LIMIT) {
      setCanCreateMore(false);
      setMessage(`You have reached the limit of ${FREE_TIER_INVOICE_LIMIT} invoices for the free tier.`);
    } else {
      setCanCreateMore(true);
      setMessage('');
    }
  }, [currentInvoiceCount]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userId || !canCreateMore) {
      setMessage(canCreateMore ? 'User not identified.' : `Invoice limit reached (${FREE_TIER_INVOICE_LIMIT}).`);
      return;
    }
    setLoading(true);
    setMessage('');

    const calculatedTotal = Number(itemQuantity) * Number(itemUnitPrice);
    if (isNaN(calculatedTotal)) {
        setMessage('Error: Invalid quantity or unit price.');
        setLoading(false);
        return;
    }

    const newInvoiceData: NewInvoice = {
      invoice_number: invoiceNumber || `INV-${Date.now().toString().slice(-6)}`, // Basic auto-generation
      client_name: clientName,
      client_email: clientEmail,
      issue_date: issueDate,
      due_date: dueDate,
      total_amount: calculatedTotal, // Use calculated total
      status: 'draft' as InvoiceStatus,
      items: [{
        description: itemDescription,
        quantity: Number(itemQuantity),
        unit_price: Number(itemUnitPrice),
        total: calculatedTotal
      }],
      notes: '', // Can add a field for this
    };

    try {
      const { data, error } = await supabase
        .from('invoices')
        .insert([{ ...newInvoiceData, user_id: userId }])
        .select()
        .single(); // Assuming insert returns the created row

      if (error) throw error;
      if (data) {
        setMessage('Invoice created successfully!');
        onInvoiceCreated(data as Invoice);
        // Reset form
        setClientName('');
        setClientEmail('');
        setInvoiceNumber('');
        setIssueDate(new Date().toISOString().split('T')[0]);
        setDueDate('');
        setTotalAmount('');
        setItemDescription('Service/Product');
        setItemQuantity(1);
        setItemUnitPrice('');
      }
    } catch (error: any) {
      console.error('Error creating invoice:', error);
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!userId) {
    return <p>Please sign in to create invoices.</p>;
  }

  if (!canCreateMore && currentInvoiceCount >= FREE_TIER_INVOICE_LIMIT) {
     return <p style={{ color: 'orange' }}>{message || `Invoice limit of ${FREE_TIER_INVOICE_LIMIT} reached.`}</p>;
  }

  return (
    <form onSubmit={handleSubmit} style={{ padding: '20px', border: '1px solid #eee', borderRadius: '8px', marginBottom: '20px' }}>
      <h3>Create New Invoice</h3>
      <div>
        <label>Invoice Number: <input type="text" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} placeholder="Optional, auto-generated if blank" /></label>
      </div>
      <div>
        <label>Client Name: <input type="text" value={clientName} onChange={(e) => setClientName(e.target.value)} required /></label>
      </div>
      <div>
        <label>Client Email: <input type="email" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} /></label>
      </div>
      <div>
        <label>Issue Date: <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} required /></label>
      </div>
      <div>
        <label>Due Date: <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required /></label>
      </div>

      <h4>Item</h4>
       <div>
        <label>Description: <input type="text" value={itemDescription} onChange={(e) => setItemDescription(e.target.value)} required /></label>
      </div>
      <div>
        <label>Quantity: <input type="number" value={itemQuantity} onChange={(e) => setItemQuantity(Number(e.target.value))} min="0" step="any" required /></label>
      </div>
      <div>
        <label>Unit Price: <input type="number" value={itemUnitPrice} onChange={(e) => setItemUnitPrice(Number(e.target.value))} min="0" step="0.01" required /></label>
      </div>
      <p>Calculated Total: {(Number(itemQuantity) * Number(itemUnitPrice)).toFixed(2)}</p>


      <button type="submit" disabled={loading || !canCreateMore}>
        {loading ? 'Creating...' : 'Create Invoice'}
      </button>
      {message && <p style={{ color: message.startsWith('Error:') ? 'red' : 'green', marginTop: '10px' }}>{message}</p>}
    </form>
  );
}
