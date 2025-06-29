import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { Invoice } from '@/types/invoice';
import InvoiceForm from './InvoiceForm';
import InvoiceList from './InvoiceList';

interface InvoicesPageProps {
  userId: string | undefined;
}

export default function InvoicesPage({ userId }: InvoicesPageProps) {
  const [currentInvoiceCount, setCurrentInvoiceCount] = useState(0);
  // This state is to trigger a refresh of the list if needed,
  // though direct prop drilling of count might be enough.
  const [invoices, setInvoices] = useState<Invoice[]>([]);


  // Callback for InvoiceList to update the count
  const handleInvoiceCountChange = (count: number) => {
    setCurrentInvoiceCount(count);
  };

  // Callback for InvoiceForm when a new invoice is created
  const handleInvoiceCreated = (newInvoice: Invoice) => {
    // Increment count and add to a local list to force re-render of InvoiceList
    // or rely on InvoiceList to re-fetch.
    // For simplicity, we'll update the count, which should prompt InvoiceList to update.
    setCurrentInvoiceCount(prevCount => prevCount + 1);
    setInvoices(prevInvoices => [newInvoice, ...prevInvoices]); // Add to local list for immediate UI update
    // InvoiceList will also re-fetch based on its own logic if userId changes or on mount,
    // but adding here provides a more responsive feel.
    // The source of truth remains the DB, so a full re-fetch by InvoiceList is good.
  };

  // Effect to sync invoices state with InvoiceList's internal state if needed,
  // or primarily, to manage the list if InvoiceList doesn't manage its own state from props.
  // Since InvoiceList fetches its own data, this local `invoices` state here is mostly for triggering
  // re-renders or if we wanted to pass the list down.
  // The current InvoiceList fetches its own data, so this local `invoices` state isn't strictly necessary
  // for InvoiceList's operation but can be useful for other things on this page.

  if (!userId) {
    return <p>Loading user information or user not signed in.</p>;
  }

  return (
    <div>
      <h2>Invoices</h2>
      <InvoiceForm
        userId={userId}
        currentInvoiceCount={currentInvoiceCount}
        onInvoiceCreated={handleInvoiceCreated}
      />
      <InvoiceList
        userId={userId}
        onInvoiceCountChange={handleInvoiceCountChange}
        // onInvoiceSelect can be implemented later for viewing/editing single invoice
      />
      <p style={{ marginTop: '10px', fontSize: '0.9em', color: '#555' }}>
        Invoice count: {currentInvoiceCount} / 100 (Free Tier Limit)
      </p>
    </div>
  );
}
