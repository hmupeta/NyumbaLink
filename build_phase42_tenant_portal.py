#!/usr/bin/env python3
"""NyumbaLink Phase 42: Mobile Tenant Portal."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ----------------------------------------------------------------
# 1. Backend: Expose "My Tenancy" endpoint on LeaseViewSet
# ----------------------------------------------------------------
LEASE_VIEWS = ROOT / "apps" / "management" / "views.py"
text = LEASE_VIEWS.read_text(encoding="utf-8")

if "def my_tenancy(self, request):" not in text:
    new_action = '''
    @action(detail=False, methods=["get"])
    def my_tenancy(self, request):
        """Returns all active leases where the requesting user is the tenant."""
        from django.db.models import Q
        leases = Lease.objects.filter(
            Q(tenant_email__iexact=request.user.email) |
            Q(tenant_email="")
        ).exclude(tenant_email="").prefetch_related("rent_records")
        return Response(self.get_serializer(leases, many=True).data)
'''
    # Ensure `action` and `Response` are imported
    if "from rest_framework.decorators import action" not in text:
        text = "from rest_framework.decorators import action\nfrom rest_framework.response import Response\n" + text
    # Inject action before the end of the class (after perform_create)
    if "class LeaseViewSet(viewsets.ModelViewSet):" in text:
        text = text.replace(
            "    def perform_create(self, serializer):",
            new_action + "\n    def perform_create(self, serializer):"
        )
    LEASE_VIEWS.write_text(text, encoding="utf-8")
    print("✅ Patched management/views.py: Added my_tenancy endpoint")

# ----------------------------------------------------------------
# 2. Backend: Allow tenants to create/view Maintenance Requests
# ----------------------------------------------------------------
MAINT_VIEWS = ROOT / "apps" / "maintenance" / "views.py"
text = MAINT_VIEWS.read_text(encoding="utf-8")

if "tenant_email__iexact" not in text:
    new_views = '''from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from .models import MaintenanceRequest
from .serializers import MaintenanceRequestSerializer
from apps.management.models import Lease
from apps.notifications.services import create_notification


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MaintenanceRequest.objects.filter(
            Q(landlord=user) | Q(lease__tenant_email__iexact=user.email)
        ).select_related("property", "lease")

    def perform_create(self, serializer):
        lease_id = self.request.data.get('lease')
        if lease_id:
            try:
                lease = Lease.objects.get(id=lease_id)
            except Lease.DoesNotExist:
                raise PermissionDenied("Lease not found.")
            
            is_landlord = lease.landlord_id == self.request.user.id
            is_tenant = lease.tenant_email.lower() == self.request.user.email.lower()
            if not (is_landlord or is_tenant):
                raise PermissionDenied("You cannot log maintenance for this lease.")
            
            instance = serializer.save(landlord=lease.landlord, property=lease.property)
            
            # Notify landlord if a tenant submitted
            if is_tenant and not is_landlord:
                create_notification(
                    user=lease.landlord,
                    title="New Maintenance Issue",
                    message=f"{self.request.user.email} reported: {instance.title}",
                    link="/dashboard?tab=maintenance",
                )
        else:
            serializer.save(landlord=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        req = self.get_object()
        if req.landlord_id != request.user.id:
            return Response({"detail": "Only the landlord can update status."}, status=403)
            
        new_status = request.data.get("status")
        note = request.data.get("resolution_note", "")
        if new_status not in ["OPEN", "IN_PROGRESS", "RESOLVED"]:
            return Response({"detail": "Invalid status"}, status=400)
            
        req.status = new_status
        req.resolution_note = note
        if new_status == "RESOLVED":
            req.resolved_at = timezone.now()
        req.save()
        return Response(MaintenanceRequestSerializer(req).data)
'''
    MAINT_VIEWS.write_text(new_views, encoding="utf-8")
    print("✅ Patched maintenance/views.py: Tenant can now create/view requests")

print("\n🚀 Pushing backend changes to GitHub...")
subprocess.run(["git", "add", "apps/management/views.py", "apps/maintenance/views.py"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Tenant can view leases and submit maintenance"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

# ----------------------------------------------------------------
# 3. Flutter: Update API Client
# ----------------------------------------------------------------
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "getMyTenancy" not in text:
    text = text.replace(
        "  // --- Maintenance ---",
        '''  static Future<List<dynamic>> getMyTenancy() async {
    final res = await http.get(Uri.parse('$baseUrl/leases/my_tenancy/'), headers: await getHeaders());
    if (res.statusCode == 200) return jsonDecode(res.body);
    throw Exception('Failed to load tenancy');
  }

  static Future<void> createMaintenanceRequest(Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl/maintenance/'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (res.statusCode != 201) throw Exception('Failed to log maintenance');
  }

  // --- Maintenance ---'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added tenant endpoints")

# ----------------------------------------------------------------
# 4. Flutter: Create Tenant Portal Screen
# ----------------------------------------------------------------
TENANT_PORTAL = '''
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'api_client.dart';

class TenantPortalScreen extends StatefulWidget {
  @override
  _TenantPortalScreenState createState() => _TenantPortalScreenState();
}

class _TenantPortalScreenState extends State<TenantPortalScreen> {
  late Future<List<dynamic>> _leasesFuture;

  @override
  void initState() {
    super.initState();
    _leasesFuture = ApiClient.getMyTenancy();
  }

  void _showMaintenanceDialog(String leaseId) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    String priority = 'MEDIUM';

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setStateDialog) {
          return AlertDialog(
            title: Text("Report an Issue"),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: titleCtrl,
                    decoration: InputDecoration(labelText: "Issue Title", border: OutlineInputBorder()),
                  ),
                  SizedBox(height: 12),
                  TextField(
                    controller: descCtrl,
                    decoration: InputDecoration(labelText: "Description", border: OutlineInputBorder()),
                    maxLines: 3,
                  ),
                  SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: priority,
                    decoration: InputDecoration(labelText: "Priority", border: OutlineInputBorder()),
                    items: ['LOW', 'MEDIUM', 'HIGH'].map((p) => DropdownMenuItem(value: p, child: Text(p))).toList(),
                    onChanged: (val) => setStateDialog(() => priority = val!),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context), child: Text("Cancel")),
              ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                onPressed: () async {
                  if (titleCtrl.text.isEmpty || descCtrl.text.isEmpty) return;
                  Navigator.pop(context);
                  try {
                    await ApiClient.createMaintenanceRequest({
                      'title': titleCtrl.text,
                      'description': descCtrl.text,
                      'priority': priority,
                      'lease': leaseId,
                    });
                    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Issue reported to landlord!")));
                  } catch (e) {
                    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                },
                child: Text("Submit"),
              ),
            ],
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("My Tenancy"), backgroundColor: Color(0xFF059669)),
      body: FutureBuilder<List<dynamic>>(
        future: _leasesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading tenancy"));

          final leases = snapshot.data!;
          if (leases.isEmpty) {
            return Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  "You have no active leases. If you are a tenant, please ask your landlord to add you.",
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.grey),
                ),
              ),
            );
          }

          return ListView.builder(
            padding: EdgeInsets.all(16),
            itemCount: leases.length,
            itemBuilder: (context, index) {
              final lease = leases[index];
              final records = lease['rent_records'] as List<dynamic>? ?? [];
              final pending = records.where((r) => r['status'] == 'PENDING').toList();

              return Card(
                margin: EdgeInsets.only(bottom: 16),
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(lease['property_name'], style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                      SizedBox(height: 4),
                      Text("Monthly Rent: ${lease['monthly_rent']} ZMW", style: TextStyle(color: Colors.grey[700])),
                      SizedBox(height: 4),
                      Text("Lease Ends: ${DateFormat('MMM d, yyyy').format(DateTime.parse(lease['end_date']))}", style: TextStyle(color: Colors.grey[600], fontSize: 12)),
                      
                      Divider(height: 32),
                      
                      Text("Rent Schedule", style: TextStyle(fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      ...records.take(6).map((r) {
                        final isPaid = r['status'] == 'PAID';
                        return ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(isPaid ? Icons.check_circle : Icons.schedule, color: isPaid ? Colors.green : Colors.orange),
                          title: Text(DateFormat('MMM yyyy').format(DateTime.parse(r['due_date']))),
                          subtitle: Text("K${r['amount']}"),
                          trailing: Text(
                            isPaid ? "Paid" : "Due",
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: isPaid ? Colors.green : Colors.orange,
                            ),
                          ),
                        );
                      }),
                      
                      SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () => _showMaintenanceDialog(lease['id']),
                          icon: Icon(Icons.build, color: Colors.blue),
                          label: Text("Report Maintenance Issue", style: TextStyle(color: Colors.blue)),
                          style: OutlinedButton.styleFrom(side: BorderSide(color: Colors.blue)),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
'''
(LIB / "tenant_portal_screen.dart").write_text(TENANT_PORTAL.strip() + "\n", encoding="utf-8")
print("✅ Created tenant_portal_screen.dart")

# ----------------------------------------------------------------
# 5. Flutter: Link Tenant Portal in Profile
# ----------------------------------------------------------------
PROFILE_FILE = LIB / "profile_screen.dart"
text = PROFILE_FILE.read_text(encoding="utf-8")

if "TenantPortalScreen" not in text:
    text = text.replace(
        "import 'landlord_dashboard_screen.dart';",
        "import 'landlord_dashboard_screen.dart';\nimport 'tenant_portal_screen.dart';"
    )
    
    # Add Tenant Portal link before "My Properties"
    old_landlord = '''                ListTile(
                  leading: Icon(Icons.home_work, color: Color(0xFF059669)),
                  title: Text("My Properties (Landlord)"),'''
    
    new_tenant = '''                ListTile(
                  leading: Icon(Icons.vpn_key, color: Colors.orange[700]),
                  title: Text("My Tenancy (Tenant)"),
                  trailing: Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => TenantPortalScreen())),
                ),
                ListTile(
                  leading: Icon(Icons.home_work, color: Color(0xFF059669)),
                  title: Text("My Properties (Landlord)"),'''
    
    text = text.replace(old_landlord, new_tenant)
    PROFILE_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched profile_screen.dart: Added Tenant Portal link")

print("""
==================================================
🎉 PHASE 42 COMPLETE: TENANT PORTAL
==================================================

Go back to your terminal, quit ('q'), and restart the app.

### How to test:
1. As a landlord (demo@nyumbalink.com), go to My Properties -> Tenants. Add a new tenant with:
   - Name: "John Test"
   - Email: `seeker@nyumbalink.com` (use an existing user!)
   - Rent: 5000
   - Start Date: today
   - End Date: next year

2. Log out and log in as `seeker@nyumbalink.com`.
3. Go to Profile -> **My Tenancy (Tenant)**.
4. You will see your lease, the rent schedule, and a "Report Maintenance Issue" button.
5. Submit an issue. Now log back in as the landlord and check the Maintenance tab — the issue will be there!
""")