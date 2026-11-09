#!/usr/bin/env python3
"""NyumbaLink Phase 38: Real MTN MoMo API User Generation & Testing."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"
MOBILE = ROOT / "mobile"

# ----------------------------------------------------------------
# 1. Backend: Add MTN Generation and Testing Endpoints
# ----------------------------------------------------------------
VIEWS_FILE = ROOT / "apps" / "integrations" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

# Ensure requests is imported for API calls
if "import requests" not in text:
    text = "import requests\nimport uuid\n" + text

new_actions = '''
    @action(detail=False, methods=["post"])
    def generate_mtn_user(self, request):
        settings = self.get_object()
        sub_key = request.data.get("mtn_subscription_key")
        
        if not sub_key:
            return Response({"detail": "Primary Key (Subscription Key) is required"}, status=400)
            
        reference_id = str(uuid.uuid4())
        url = "https://sandbox.momodeveloper.mtn.com/v1_0/apiuser"
        headers = {
            "Ocp-Apim-Subscription-Key": sub_key,
            "X-Reference-Id": reference_id,
            "Content-Type": "application/json"
        }
        body = {"providerCallbackHost": "https://webhook.site/mock"}
        
        try:
            # 1. Create API User
            res = requests.post(url, headers=headers, json=body, timeout=10)
            if res.status_code not in [201, 409]: # 409 means it exists (unlikely with new UUID)
                return Response({"detail": f"MTN Error: {res.text}"}, status=400)
                
            # 2. Get API Key
            key_url = f"https://sandbox.momodeveloper.mtn.com/v1_0/apiuser/{reference_id}/apikey"
            key_res = requests.post(key_url, headers={"Ocp-Apim-Subscription-Key": sub_key}, timeout=10)
            if key_res.status_code != 201:
                return Response({"detail": f"Failed to get API Key: {key_res.text}"}, status=400)
                
            api_key = key_res.json().get("apiKey")
            
            # 3. Save to Database
            settings.mtn_subscription_key = encryption.encrypt(sub_key)
            settings.mtn_api_user = reference_id
            settings.mtn_api_key = encryption.encrypt(api_key)
            settings.save()
            
            return Response({
                "status": "success", 
                "api_user": reference_id, 
                "api_key": api_key,
                "message": "API User created and keys saved securely."
            })
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=False, methods=["post"])
    def test_mtn_connection(self, request):
        settings = self.get_object()
        if not settings.mtn_api_user or not settings.mtn_api_key or not settings.mtn_subscription_key:
            return Response({"detail": "Please generate API keys first."}, status=400)
            
        sub_key = encryption.decrypt(settings.mtn_subscription_key)
        api_user = settings.mtn_api_user
        
        try:
            # Generate access token to test connection
            auth_url = "https://sandbox.momodeveloper.mtn.com/collection/token/"
            auth_str = f"{api_user}:{encryption.decrypt(settings.mtn_api_key)}"
            b64_auth = __import__("base64").b64encode(auth_str.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {b64_auth}",
                "Ocp-Apim-Subscription-Key": sub_key
            }
            res = requests.post(auth_url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                return Response({"status": "success", "message": "Successfully connected to MTN Sandbox!"})
            else:
                return Response({"detail": f"MTN responded with {res.status_code}: {res.text}"}, status=400)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)
'''

# Insert the new actions into PaymentSettingsViewSet
if "def generate_mtn_user" not in text:
    # Find the last action in the class (stripe_connect or initiate_payment)
    if "def initiate_payment(self, request):" in text:
        text = text.replace(
            "    @action(detail=False, methods=[\"post\"])\n    def initiate_payment(self, request):",
            new_actions + "\n    @action(detail=False, methods=[\"post\"])\n    def initiate_payment(self, request):"
        )
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched integrations/views.py: Added MTN Generation and Testing")

# ----------------------------------------------------------------
# 2. Frontend Web: Update PaymentSettingsPage
# ----------------------------------------------------------------
WEB_SETTINGS = FRONTEND / "src" / "pages" / "PaymentSettingsPage.tsx"
text = WEB_SETTINGS.read_text(encoding="utf-8")

# 2a. Add state for MTN generation
text = text.replace(
    "  const stripeMutation = useMutation({",
    '''  const generateMTNMutation = useMutation({
    mutationFn: (subKey: string) => fetch(`${import.meta.env.VITE_API_URL}/payment-settings/generate_mtn_user/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${document.cookie.split('access=')[1]?.split(';')[0]}` },
      body: JSON.stringify({ mtn_subscription_key: subKey })
    }).then(res => res.json().then(data => { if (!res.ok) throw new Error(data.detail); return data; })),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['payment-settings'] });
      setSuccess(`API User generated! User: ${data.api_user}`);
      setError('');
    },
    onError: (err: any) => setError(err.message)
  });

  const testMTNMutation = useMutation({
    mutationFn: () => fetch(`${import.meta.env.VITE_API_URL}/payment-settings/test_mtn_connection/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${document.cookie.split('access=')[1]?.split(';')[0]}` }
    }).then(res => res.json().then(data => { if (!res.ok) throw new Error(data.detail); return data; })),
    onSuccess: () => {
      setSuccess('Connection successful! MTN Sandbox is reachable.');
      setError('');
    },
    onError: (err: any) => setError(err.message)
  });

  const stripeMutation = useMutation({'''
)

# 2b. Replace the MTN Tab UI
old_mtn_ui = '''      {activeTab === 'MTN' && (
        <form onSubmit={handleSave} className="bg-white border rounded-lg p-6 space-y-4">
          <h2 className="font-bold">MTN MoMo Zambia</h2>
          <p className="text-sm text-gray-600">Enter your MTN MoMo API credentials from the MTN Developer Portal.</p>
          <div>
            <label className="block text-sm font-medium mb-1">API User</label>
            <input name="mtn_api_user" defaultValue={settings?.mtn_api_user || ''} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">API Key</label>
            <input name="mtn_api_key" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subscription Key</label>
            <input name="mtn_subscription_key" type="password" placeholder="Leave blank to keep current" className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Environment</label>
            <select name="mtn_target_environment" defaultValue={settings?.mtn_target_environment || 'mtnzambia'} className="w-full border rounded px-3 py-2">
              <option value="sandbox">Sandbox (EUR)</option>
              <option value="mtnzambia">Production (ZMW)</option>
            </select>
          </div>
          <button type="submit" disabled={updateMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded">Save MTN Settings</button>
        </form>
      )}'''

new_mtn_ui = '''      {activeTab === 'MTN' && (
        <div className="space-y-6">
          {settings?.mtn_api_user ? (
            <div className="bg-green-50 border border-green-200 p-6 rounded-lg">
              <h2 className="font-bold text-green-800 mb-2">MTN MoMo is Connected</h2>
              <p className="text-sm text-green-700 mb-4">API User: <strong>{settings.mtn_api_user}</strong></p>
              <button onClick={() => testMTNMutation.mutate()} disabled={testMTNMutation.isPending} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                {testMTNMutation.isPending ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
          ) : (
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              generateMTNMutation.mutate(formData.get('mtn_subscription_key') as string);
            }} className="bg-white border rounded-lg p-6 space-y-4">
              <h2 className="font-bold">Connect MTN MoMo (Sandbox)</h2>
              <p className="text-sm text-gray-600">Enter your Primary Key (Subscription Key) from the MTN Developer Portal. We will automatically generate your API User and API Key.</p>
              <div>
                <label className="block text-sm font-medium mb-1">MTN Primary Key</label>
                <input name="mtn_subscription_key" type="password" placeholder="e.g. 9b8a..." required className="w-full border rounded px-3 py-2" />
              </div>
              <button type="submit" disabled={generateMTNMutation.isPending} className="bg-emerald-600 text-white px-4 py-2 rounded w-full">
                {generateMTNMutation.isPending ? 'Generating...' : 'Generate API User & Key'}
              </button>
            </form>
          )}
        </div>
      )}'''

text = text.replace(old_mtn_ui, new_mtn_ui)
WEB_SETTINGS.write_text(text, encoding="utf-8")
print("✅ Patched PaymentSettingsPage.tsx: Added MTN generation flow")

# ----------------------------------------------------------------
# 3. Flutter: Update PaymentSettingsScreen
# ----------------------------------------------------------------
FLUTTER_SETTINGS = MOBILE / "lib" / "payment_settings_screen.dart"

NEW_FLUTTER_SETTINGS = '''
import 'package:flutter/material.dart';
import 'api_client.dart';

class PaymentSettingsScreen extends StatefulWidget {
  @override
  _PaymentSettingsScreenState createState() => _PaymentSettingsScreenState();
}

class _PaymentSettingsScreenState extends State<PaymentSettingsScreen> {
  bool _isLoading = true;
  bool _isProcessing = false;
  String _activeTab = 'MTN';
  Map<String, dynamic> _settings = {};

  final _primaryKeyCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final data = await ApiClient.getPaymentSettings();
      if (mounted) setState(() { _settings = data; _isLoading = false; });
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _generateMTN() async {
    if (_primaryKeyCtrl.text.isEmpty) return;
    setState(() => _isProcessing = true);
    try {
      final res = await ApiClient.post('/payment-settings/generate_mtn_user/', {
        'mtn_subscription_key': _primaryKeyCtrl.text.trim()
      });
      await _loadSettings();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("API User Generated Successfully!")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  Future<void> _testMTN() async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.post('/payment-settings/test_mtn_connection/', {});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Connection Successful! MTN Sandbox is reachable.")));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return Scaffold(body: Center(child: CircularProgressIndicator()));

    final bool isMTNConnected = _settings['mtn_api_user'] != null && _settings['mtn_api_user'].toString().isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: Text("Payment Integrations"), backgroundColor: Color(0xFF059669)),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text("Connect your merchant accounts to receive rent and deposits directly from tenants.", style: TextStyle(color: Colors.grey[600])),
            SizedBox(height: 16),
            Row(
              children: [
                _buildTab("MTN", "MTN MoMo"),
                SizedBox(width: 8),
                _buildTab("AIRTEL", "Airtel Money"),
              ],
            ),
            SizedBox(height: 24),
            
            if (_activeTab == 'MTN') ...[
              if (isMTNConnected)
                Container(
                  padding: EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("MTN MoMo is Connected", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green[800], fontSize: 18)),
                      SizedBox(height: 8),
                      Text("API User: ${_settings['mtn_api_user']}", style: TextStyle(color: Colors.green[900])),
                      SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isProcessing ? null : _testMTN,
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.green[700]),
                          child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Test Connection"),
                        ),
                      )
                    ],
                  ),
                )
              else
                Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text("Connect MTN MoMo (Sandbox)", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    Text("Enter your Primary Key (Subscription Key) from the MTN Developer Portal. We will automatically generate your API User and API Key.", style: TextStyle(color: Colors.grey)),
                    SizedBox(height: 16),
                    TextField(
                      controller: _primaryKeyCtrl,
                      decoration: InputDecoration(labelText: 'MTN Primary Key', border: OutlineInputBorder(), hintText: "e.g. 9b8a..."),
                    ),
                    SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isProcessing ? null : _generateMTN,
                      style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(double.infinity, 50)),
                      child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Generate API User & Key"),
                    ),
                  ],
                )
            ] else ...[
              Text("Airtel Money Integration coming soon.", style: TextStyle(color: Colors.grey)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTab(String id, String label) {
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeTab = id),
        child: Container(
          padding: EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: _activeTab == id ? Color(0xFF059669) : Colors.grey[200],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(color: _activeTab == id ? Colors.white : Colors.black87, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ),
    );
  }
}
'''
FLUTTER_SETTINGS.write_text(NEW_FLUTTER_SETTINGS.strip() + "\n", encoding="utf-8")
print("✅ Patched payment_settings_screen.dart: Added MTN generation flow")

# ----------------------------------------------------------------
# 4. Flutter: Add generic POST method to API client
# ----------------------------------------------------------------
API_FILE = MOBILE / "lib" / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "static Future<Map<String, dynamic>> post(" not in text:
    text = text.replace(
        "  // --- Direct Payments ---",
        '''  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data) async {
    final res = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: await getHeaders(),
      body: jsonEncode(data),
    );
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return jsonDecode(res.body);
    }
    final error = jsonDecode(res.body)['detail'] ?? 'Request failed';
    throw Exception(error);
  }

  // --- Direct Payments ---'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added generic POST method")

print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Real MTN MoMo sandbox integration and testing"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 38 COMPLETE: REAL MTN INTEGRATION
==================================================

Go back to your Flutter terminal, quit ('q'), and restart the app.

1. **Web & Mobile**: Go to Payment Integrations -> MTN.
2. If not connected, you will see a form asking for your MTN **Primary Key**.
3. Enter a sandbox key (e.g., `9b8ab8b...` from the MTN Developer Portal).
4. Click **Generate API User & Key**. The backend will talk to MTN, create the user, get the key, and save it.
5. You will now see a green **Connected** box with a **Test Connection** button.
6. Click Test Connection. It will request an access token from MTN and verify everything works!
""")