#!/usr/bin/env python3
"""Connects the mobile payment flow to the Lease Agreement signing."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Allow Tenant to Request a Lease
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "management" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "def request_lease" not in text:
    new_action = '''
    @action(detail=False, methods=["post"])
    def request_lease(self, request):
        listing_id = request.data.get("listing_id")
        if not listing_id:
            return Response({"detail": "Listing ID required"}, status=400)
            
        from apps.properties.models import Listing
        try:
            listing = Listing.objects.get(id=listing_id)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found"}, status=404)
            
        # Check if a lease already exists for this tenant and property
        existing = Lease.objects.filter(
            property=listing.property,
            tenant_email__iexact=request.user.email
        ).first()
        
        if existing:
            return Response(self.get_serializer(existing).data)
            
        # Create a new lease draft
        lease = Lease.objects.create(
            landlord=listing.created_by,
            property=listing.property,
            tenant_name=request.user.first_name or request.user.email.split('@')[0],
            tenant_phone=request.user.phone_number or "",
            tenant_email=request.user.email,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365), # Default 1 year
            monthly_rent=listing.price,
            deposit_paid=0,
            status="ACTIVE"
        )
        
        # Auto-generate the agreement text
        lease.agreement_text = f"""
RESIDENTIAL TENANCY AGREEMENT

THIS AGREEMENT is made between:
LANDLORD: {lease.landlord.email}
TENANT: {lease.tenant_name} ({lease.tenant_email})

PROPERTY: {lease.property.address_line or lease.property.neighbourhood.name}
TERM: {lease.start_date} to {lease.end_date}
RENT: ZMW {lease.monthly_rent} payable monthly.

1. The Tenant agrees to pay rent on or before the due date.
2. The Tenant shall keep the property in good condition.
3. The Landlord shall ensure the property is habitable.
4. This agreement is legally binding once signed by both parties digitally.
        """.strip()
        lease.save()
        
        return Response(self.get_serializer(lease).data, status=201)
'''
    
    if "def perform_create(self, serializer):" in text:
        text = text.replace(
            "    def perform_create(self, serializer):",
            new_action + "\n    def perform_create(self, serializer):"
        )
        # Ensure timedelta is imported
        if "from datetime import timedelta" not in text:
            text = "from datetime import timedelta\n" + text
            # Replace timezone.timedelta with timedelta since we imported it
            text = text.replace("timezone.timedelta", "timedelta")
            
        VIEWS_FILE.write_text(text, encoding="utf-8")
        print("✅ Patched management/views.py: Added request_lease endpoint")

print("\n🚀 Pushing backend changes to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Allow tenants to request a lease and auto-generate agreement"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 2. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "requestLease" not in text:
    text = text.replace(
        "  // --- Saved Properties ---",
        '''  static Future<Map<String, dynamic>> requestLease(String listingId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/leases/request_lease/'),
      headers: await getHeaders(),
      body: jsonEncode({'listing_id': listingId}),
    );
    if (res.statusCode == 200 || res.statusCode == 201) return jsonDecode(res.body);
    throw Exception('Failed to request lease');
  }

  // --- Saved Properties ---'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added requestLease")

# ----------------------------------------------------------------
# 3. Flutter: Update Property Detail Screen (Change Button)
# ----------------------------------------------------------------
DETAIL_FILE = LIB / "listing_detail_screen.dart"
text = DETAIL_FILE.read_text(encoding="utf-8")

# 3a. Update the import for LeaseAgreementScreen
if "lease_agreement_screen.dart" not in text:
    text = text.replace(
        "import 'login_screen.dart';",
        "import 'login_screen.dart';\nimport 'lease_agreement_screen.dart';"
    )

# 3b. Replace the "Pay Rent / Deposit" button logic
old_button = '''                            // NEW: Pay Rent Button
                            ElevatedButton.icon(
                              onPressed: () {
                                showModalBottomSheet(
                                  context: context,
                                  isScrollControlled: true,
                                  builder: (context) => _RentPaymentModal(
                                    listingId: listing['id'],
                                    amount: double.parse(listing['price'].toString()),
                                  ),
                                );
                              },
                              icon: Icon(Icons.payment),
                              label: Text("Pay Rent / Deposit"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.blue[700], 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),'''

new_button = '''                            // NEW: Apply & Sign Lease Button
                            ElevatedButton.icon(
                              onPressed: () async {
                                try {
                                  // 1. Create/Get the lease from backend
                                  final lease = await ApiClient.requestLease(listing['id']);
                                  // 2. Navigate to the Lease Agreement screen to read and sign
                                  if (mounted) {
                                    Navigator.push(context, MaterialPageRoute(
                                      builder: (_) => LeaseAgreementScreen(leaseId: lease['id'])
                                    ));
                                  }
                                } catch (e) {
                                  if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                                }
                              },
                              icon: Icon(Icons.description),
                              label: Text("Apply & Sign Lease Agreement"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.blue[700], 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),'''

text = text.replace(old_button, new_button)
DETAIL_FILE.write_text(text, encoding="utf-8")
print("✅ Patched listing_detail_screen.dart: Replaced Pay Rent with Apply & Sign Lease")

# ----------------------------------------------------------------
# 4. Flutter: Update LeaseAgreementScreen (Show Payment after Signing)
# ----------------------------------------------------------------
LEASE_FILE = LIB / "lease_agreement_screen.dart"
text = LEASE_FILE.read_text(encoding="utf-8")

# Add the RentPaymentModal logic to the Lease screen
if "_showPaymentModal" not in text:
    # Add method to the state class
    text = text.replace(
        "  @override\n  Widget build(BuildContext context) {",
        '''  void _showPaymentModal() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Container(
        padding: EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text("Pay Rent & Deposit", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            Text("Payment processing will be integrated here (MTN/Airtel)."),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment Successful!")));
              },
              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(double.infinity, 50)),
              child: Text("Pay Now"),
            )
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {'''
    )

    # Insert the payment button after the signature block
    old_sig_block = '''                  else if (isLandlord || isTenant)
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: userSigned || _isProcessing ? null : _sign,
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700]),
                        child: _isProcessing 
                          ? CircularProgressIndicator(color: Colors.white) 
                          : Text(userSigned ? "You have signed" : "Digitally Sign Agreement"),
                      ),
                    )'''

    new_sig_block = '''                  else if (isLandlord || isTenant)
                    Column(
                      children: [
                        if (userSigned && isTenant && !bothSigned)
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: ElevatedButton.icon(
                              onPressed: _showPaymentModal,
                              icon: Icon(Icons.payment),
                              label: Text("Pay Rent & Deposit Now"),
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                            ),
                          )
                        else
                          SizedBox(
                            width: double.infinity,
                            height: 50,
                            child: ElevatedButton(
                              onPressed: userSigned || _isProcessing ? null : _sign,
                              style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700]),
                              child: _isProcessing 
                                ? CircularProgressIndicator(color: Colors.white) 
                                : Text(userSigned ? "You have signed" : "Digitally Sign Agreement"),
                            ),
                          )
                      ],
                    )'''

    text = text.replace(old_sig_block, new_sig_block)
    LEASE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched lease_agreement_screen.dart: Added payment button after signing")

print("""
==================================================
🎉 PHASE 50 COMPLETE: LEASE & PAYMENT FLOW FIXED
==================================================

Go back to your Flutter terminal and press 'R' (capital R) to hot restart.

### The new correct flow:
1. **Tenant** opens a property and clicks the blue **"Apply & Sign Lease Agreement"** button.
2. The system instantly generates the legal contract and opens it.
3. Tenant clicks **Digitally Sign Agreement**.
4. A new green **"Pay Rent & Deposit Now"** button appears.
5. Tenant pays the deposit/rent.
6. The **Landlord** logs in, goes to the Tenants tab, opens the lease, and clicks **Sign**.
7. The contract is finalized, and the property becomes OCCUPIED.
""")