#!/usr/bin/env python3
"""NyumbaLink Phase 55: Tenant Rent Payments via MTN MoMo (Web & Mobile)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Update Views to handle Rent Payments
# ----------------------------------------------------------------
PAYMENTS_VIEWS = ROOT / "apps" / "payments" / "views.py"
text = PAYMENTS_VIEWS.read_text(encoding="utf-8")

new_views = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from apps.properties.models import Listing
from apps.management.models import RentRecord
from apps.integrations.models import PaymentTransaction
from .momo_service import initiate_momo_payment, check_momo_status
import uuid

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    rent_record_id = request.data.get('rent_record_id')
    listing_id = request.data.get('listing_id')
    amount = request.data.get('amount')
    phone = request.data.get('phone_number')
    
    if not all([amount, phone]):
        return Response({"error": "Missing required fields"}, status=400)

    landlord = None
    metadata = {'tenant_phone': phone, 'initiated_by': request.user.email}

    if rent_record_id:
        try:
            record = RentRecord.objects.get(id=rent_record_id)
            landlord = record.lease.landlord
            metadata['rent_record_id'] = str(record.id)
            # Use the exact amount from the record to prevent tampering
            amount = record.amount 
        except RentRecord.DoesNotExist:
            return Response({"error": "Rent record not found"}, status=404)
    elif listing_id:
        try:
            listing = Listing.objects.get(id=listing_id)
            landlord = listing.created_by
            metadata['listing_id'] = str(listing.id)
        except Listing.DoesNotExist:
            return Response({"error": "Listing not found"}, status=404)
    else:
        return Response({"error": "Either rent_record_id or listing_id is required"}, status=400)

    reference = f"NYL-{uuid.uuid4().hex[:8].upper()}"
    
    tx = PaymentTransaction.objects.create(
        landlord=landlord,
        amount=amount,
        currency='ZMW',
        reference=reference,
        status=PaymentTransaction.Status.PENDING,
        metadata=metadata
    )
    
    try:
        momo_ref = initiate_momo_payment(landlord, amount, phone, reference)
        tx.provider_transaction_id = momo_ref
        tx.save()
        return Response({"reference": reference, "momo_ref": momo_ref})
    except Exception as e:
        tx.status = PaymentTransaction.Status.FAILED
        tx.save()
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, reference):
    try:
        tx = PaymentTransaction.objects.get(reference=reference)
        if tx.status == PaymentTransaction.Status.PENDING and tx.provider_transaction_id:
            status = check_momo_status(tx.landlord, tx.provider_transaction_id)
            
            if status == 'SUCCESSFUL':
                tx.status = PaymentTransaction.Status.SUCCESS
                tx.save()
                
                # If this payment was for a rent record, mark it PAID
                rent_record_id = tx.metadata.get('rent_record_id')
                if rent_record_id:
                    from django.utils import timezone
                    RentRecord.objects.filter(id=rent_record_id).update(
                        status=RentRecord.Status.PAID,
                        paid_date=timezone.now().date()
                    )
            elif status == 'FAILED':
                tx.status = PaymentTransaction.Status.FAILED
                tx.save()
                
        return Response({"status": tx.status})
    except PaymentTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)
'''

PAYMENTS_VIEWS.write_text(new_views.strip() + "\n", encoding="utf-8")
print("✅ Patched apps/payments/views.py: Connected RentRecords to payments")

print("\n🚀 Pushing backend to GitHub...")
subprocess.run(["git", "add", "apps/payments/views.py"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Connect rent records to MTN payments"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 2. Web: Create MTN Payment Modal
# ----------------------------------------------------------------
WEB_MODAL = '''
import { useState, useEffect } from 'react'
import { paymentsApi } from '../api/payments'

interface Props {
  rentRecordId?: string
  listingId?: string
  amount: number
  onSuccess: () => void
  onClose: () => void
}

export default function MomoPaymentModal({ rentRecordId, listingId, amount, onSuccess, onClose }: Props) {
  const [step, setStep] = useState<'input' | 'waiting' | 'failed' | 'success'>('input')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [reference, setReference] = useState<string | null>(null)

  useEffect(() => {
    let interval: any;
    if (step === 'waiting' && reference) {
      interval = setInterval(async () => {
        try {
          const res = await paymentsApi.checkStatus(reference)
          if (res.status === 'SUCCESS') {
            setStep('success')
            setTimeout(onSuccess, 1500)
          } else if (res.status === 'FAILED') {
            setStep('failed')
            setError('Payment failed or was cancelled on your phone.')
          }
        } catch (e) { /* ignore network error */ }
      }, 5000)
    }
    return () => clearInterval(interval)
  }, [step, reference, onSuccess])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setStep('waiting')
    try {
      const res = await paymentsApi.initiatePayment({
        rent_record_id: rentRecordId,
        listing_id: listingId,
        amount,
        phone_number: phone
      })
      setReference(res.reference)
    } catch (err: any) {
      setError(err.message)
      setStep('failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold mb-4">Pay with MTN MoMo</h2>
        
        {step === 'input' && (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-gray-600">A prompt will be sent to your phone to enter your PIN.</p>
            <div>
              <label className="block text-sm font-medium mb-1">MTN Phone Number</label>
              <input required value={phone} onChange={e => setPhone(e.target.value)} placeholder="e.g. 260966456787" className="w-full border rounded px-3 py-2" />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={onClose} className="flex-1 bg-gray-100 py-2 rounded">Cancel</button>
              <button type="submit" className="flex-1 bg-emerald-600 text-white py-2 rounded font-medium">Pay K{amount}</button>
            </div>
          </form>
        )}

        {step === 'waiting' && (
          <div className="text-center py-8">
            <div className="w-12 h-12 border-4 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="font-bold">Waiting for approval...</p>
            <p className="text-sm text-gray-500 mt-2">Please check your phone and enter your MoMo PIN.</p>
          </div>
        )}

        {step === 'success' && (
          <div className="text-center py-8 text-green-600">
            <h3 className="font-bold text-xl">Payment Successful!</h3>
          </div>
        )}

        {step === 'failed' && (
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <button onClick={() => setStep('input')} className="bg-gray-800 text-white px-6 py-2 rounded">Try Again</button>
          </div>
        )}
      </div>
    </div>
  )
}
'''
(FRONTEND / "src" / "components" / "MomoPaymentModal.tsx").write_text(WEB_MODAL.strip() + "\n", encoding="utf-8")
print("✅ Created Web MomoPaymentModal.tsx")

# ----------------------------------------------------------------
# 3. Web: Update Tenant Portal to use Modal
# ----------------------------------------------------------------
# Note: The Tenant Portal is currently inside DashboardPage.tsx or TenantsList.tsx. 
# For this script, we assume it's in TenantsList.tsx
TENANTS_WEB = FRONTEND / "src" / "pages" / "TenantsList.tsx"
text = TENANTS_WEB.read_text(encoding="utf-8")

if "MomoPaymentModal" not in text:
    text = text.replace(
        "import { managementApi } from '../api/management'",
        "import { managementApi } from '../api/management'\nimport MomoPaymentModal from '../components/MomoPaymentModal'"
    )
    
    # Add state for the modal
    text = text.replace(
        "  const [expandedLease, setExpandedLease] = useState<string | null>(null)",
        "  const [expandedLease, setExpandedLease] = useState<string | null>(null)\n  const [payingRecord, setPayingRecord] = useState<any>(null)"
    )

    # Change the "Mark Paid" logic to a "Pay Now" button that opens the modal
    text = text.replace(
        '''                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'APPROVED' })} className="text-emerald-600 text-sm font-medium hover:underline">Approve</button>''',
        '''                    <button onClick={() => updateMutation.mutate({ id: v.id, status: 'APPROVED' })} className="text-emerald-600 text-sm font-medium hover:underline">Approve</button>''' # leave alone
    )
    
    # Actually, let's replace the "Mark Paid" button in the rent schedule loop
    old_btn = '''                      {record.status === 'PAID' ? (
                        <p className="text-xs text-green-700 font-medium mt-2 flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          Paid
                        </p>
                      ) : (
                        <button 
                          onClick={() => markPaidMutation.mutate({ leaseId: lease.id, recordId: record.id })}
                          className="mt-2 text-xs bg-gray-900 text-white px-2 py-1 rounded hover:bg-black w-full"
                        >
                          Mark Paid
                        </button>
                      )}'''
      
    new_btn = '''                      {record.status === 'PAID' ? (
                        <p className="text-xs text-green-700 font-medium mt-2 flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          Paid
                        </p>
                      ) : (
                        <button 
                          onClick={() => setPayingRecord(record)}
                          className="mt-2 text-xs bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700 w-full"
                        >
                          Pay Rent via MTN
                        </button>
                      )}'''
      
    if old_btn in text:
        text = text.replace(old_btn, new_btn)
        # Add the modal render at the bottom of the component
        text = text.replace(
            "    </div>\n  )\n}",
            """    </div>
    
    {payingRecord && (
      <MomoPaymentModal
        rentRecordId={payingRecord.id}
        amount={Number(payingRecord.amount)}
        onSuccess={() => {
          setPayingRecord(null);
          window.location.reload();
        }}
        onClose={() => setPayingRecord(null)}
      />
    )}
  </div>
  )
}"""
        )
        TENANTS_WEB.write_text(text, encoding="utf-8")
        print("✅ Patched Web TenantsList.tsx: Replaced 'Mark Paid' with MTN Payment")

# ----------------------------------------------------------------
# 4. Mobile: Create MomoPaymentModal
# ----------------------------------------------------------------
MOBILE_MODAL = '''
import 'dart:async';
import 'package:flutter/material.dart';
import 'api_client.dart';

class MomoPaymentModal extends StatefulWidget {
  final String? rentRecordId;
  final String? listingId;
  final double amount;
  final VoidCallback onSuccess;
  final VoidCallback onClose;

  MomoPaymentModal({this.rentRecordId, this.listingId, required this.amount, required this.onSuccess, required this.onClose});

  @override
  _MomoPaymentModalState createState() => _MomoPaymentModalState();
}

class _MomoPaymentModalState extends State<MomoPaymentModal> {
  final _phoneController = TextEditingController();
  String _status = 'input'; // 'input', 'processing', 'waiting', 'failed', 'success'
  String? _error;
  Timer? _pollTimer;
  String? _reference;

  void _initiatePayment() async {
    setState(() { _status = 'processing'; _error = null; });
    try {
      final res = await ApiClient.post('/payments/initiate/', {
        'rent_record_id': widget.rentRecordId,
        'listing_id': widget.listingId,
        'amount': widget.amount,
        'phone_number': _phoneController.text.trim(),
      });
      setState(() { _reference = res['reference']; _status = 'waiting'; });
      _startPolling();
    } catch (e) {
      setState(() { _error = e.toString(); _status = 'failed'; });
    }
  }

  void _startPolling() {
    _pollTimer = Timer.periodic(Duration(seconds: 5), (timer) async {
      try {
        final res = await ApiClient.get('/payments/status/$_reference/');
        final status = res['status'];
        if (status == 'SUCCESS') {
          timer.cancel();
          setState(() { _status = 'success'; });
          widget.onSuccess();
        } else if (status == 'FAILED') {
          timer.cancel();
          setState(() { _status = 'failed'; _error = "Payment failed or was cancelled."; });
        }
      } catch (e) {}
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text("Pay with MTN MoMo", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          SizedBox(height: 16),
          
          if (_status == 'input') ...[
            TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(labelText: "MTN Phone Number", hintText: "e.g. 260966456787", border: OutlineInputBorder()),
            ),
            SizedBox(height: 24),
            SizedBox(width: double.infinity, height: 50, child: ElevatedButton(
              onPressed: _initiatePayment,
              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
              child: Text("Request Payment"),
            )),
          ],
          
          if (_status == 'processing' || _status == 'waiting') ...[
            CircularProgressIndicator(color: Color(0xFF059669)),
            SizedBox(height: 16),
            Text(_status == 'processing' ? "Sending request..." : "Waiting for approval...", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            Text("Please enter your MoMo PIN on your phone.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
          ],
          
          if (_status == 'failed') ...[
            Icon(Icons.error, color: Colors.red, size: 60),
            SizedBox(height: 16),
            Text(_error ?? "Payment failed", textAlign: TextAlign.center, style: TextStyle(color: Colors.red)),
            SizedBox(height: 24),
            ElevatedButton(onPressed: () => setState(() => _status = 'input'), child: Text("Try Again")),
          ],
          
          if (_status == 'success') ...[
            Icon(Icons.check_circle, color: Colors.green, size: 60),
            SizedBox(height: 16),
            Text("Payment Successful!", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.green)),
            SizedBox(height: 24),
            ElevatedButton(onPressed: widget.onClose, child: Text("Done")),
          ],
        ],
      ),
    );
  }
}
'''
(LIB / "momo_payment_modal.dart").write_text(MOBILE_MODAL.strip() + "\n", encoding="utf-8")
print("✅ Created Mobile momo_payment_modal.dart")

# ----------------------------------------------------------------
# 5. Mobile: Update Tenant Portal to use Modal
# ----------------------------------------------------------------
TENANT_PORTAL = LIB / "tenant_portal_screen.dart"
text = TENANT_PORTAL.read_text(encoding="utf-8")

if "MomoPaymentModal" not in text:
    text = text.replace(
        "import 'api_client.dart';",
        "import 'api_client.dart';\nimport 'momo_payment_modal.dart';"
    )
    
    # Replace "Mark Paid" button with "Pay Now"
    old_mobile_btn = '''                      trailing: Text(
                            isPaid ? "Paid" : "Due",
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: isPaid ? Colors.green : Colors.orange,
                            ),
                          ),'''
      
    new_mobile_btn = '''                      trailing: isPaid 
                          ? Text("Paid", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green))
                          : TextButton(
                              onPressed: () {
                                showModalBottomSheet(
                                  context: context,
                                  isScrollControlled: true,
                                  builder: (context) => MomoPaymentModal(
                                    rentRecordId: r['id'],
                                    amount: double.parse(r['amount'].toString()),
                                    onSuccess: () {
                                      Navigator.pop(context);
                                      _loadViewings(); // refresh schedule
                                    },
                                    onClose: () {
                                      Navigator.pop(context);
                                      _loadViewings();
                                    },
                                  ),
                                );
                              },
                              child: Text("Pay Now", style: TextStyle(color: Color(0xFF059669), fontWeight: FontWeight.bold)),
                            ),'''
      
    if old_mobile_btn in text:
        text = text.replace(old_mobile_btn, new_mobile_btn)
        TENANT_PORTAL.write_text(text, encoding="utf-8")
        print("✅ Patched Mobile tenant_portal_screen.dart: Added MTN Pay Now button")
    else:
        print("⚠️ Could not find exact mobile rent list item. Please check manually.")

# ----------------------------------------------------------------
# 6. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Tenant Rent Payments via MTN MoMo (Web & Mobile)"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 55 COMPLETE: TENANT RENT PAYMENTS
==================================================

Render will rebuild both the frontend and backend.

### How to test:
1. **Web**: Log in as `seeker@nyumbalink.com`, go to Dashboard -> My Tenancy.
2. You will see the rent schedule. Click **Pay Rent via MTN** on a pending month.
3. Enter an MTN number (sandbox format: `260966456787`), click Pay.
4. The modal will show "Waiting for approval".
5. (In production, MTN sends a USSD prompt. In sandbox, the payment will succeed automatically).
6. Once successful, the record turns to **Paid**.
7. **Mobile**: Restart Flutter (`q`, then `flutter run -d chrome`). Go to Profile -> My Tenancy. 
8. Tap **Pay Now** on a pending record to launch the same MTN flow.
""")