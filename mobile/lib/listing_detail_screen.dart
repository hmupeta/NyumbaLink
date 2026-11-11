import 'dart:async';
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'chat_screen.dart';
import 'login_screen.dart';
import 'lease_agreement_screen.dart';
import 'landlord_profile_screen.dart';

class ListingDetailScreen extends StatefulWidget {
  final String listingId;

  ListingDetailScreen({required this.listingId});

  @override
  _ListingDetailScreenState createState() => _ListingDetailScreenState();
}

class _ListingDetailScreenState extends State<ListingDetailScreen> {
  late Future<Map<String, dynamic>> _listingFuture;
  bool _startingChat = false;
  int _currentImageIndex = 0;
  
  bool _isSaved = false;
  bool _isSaving = false;
  String? _viewingStatus;
  bool _isUnlocked = false;
  bool _isUnlocking = false;

  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId).then((data) {
      setState(() => _isUnlocked = data['is_unlocked'] ?? false);
      return data;
    });
    _checkViewingStatus();
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  Future<void> _checkViewingStatus() async {
    final auth = Provider.of<AuthProvider>(context, listen: false);
    if (auth.user == null) return;

    try {
      // If this fails or times out, we just silently ignore it and show the default button
      final requests = await ApiClient.getViewingRequests().timeout(const Duration(seconds: 4));
      final req = requests.firstWhere(
        (r) => r['listing'].toString() == widget.listingId,
        orElse: () => null,
      );
      
      if (mounted && req != null) {
        setState(() => _viewingStatus = req['status']);
      }
    } catch (e) {
      print("Viewing status check failed: $e");
    }
  }

  void _toggleSave() async {
    if (_isSaving) return;
    setState(() => _isSaving = true);
    try {
      await ApiClient.toggleSaveListing(widget.listingId, _isSaved);
      if (mounted) {
        setState(() => _isSaved = !_isSaved);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(!_isSaved ? "Removed from saved" : "Saved!")));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to save. Please log in.")));
      }
    }
    if (mounted) setState(() => _isSaving = false);
  }

  void _startChat(String listingId, String landlordName) async {
    setState(() => _startingChat = true);
    try {
      final convId = await ApiClient.startConversation(listingId);
      if (mounted) {
        Navigator.push(context, MaterialPageRoute(
          builder: (_) => ChatScreen(conversationId: convId, landlordName: landlordName),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to open chat. Please log in again.")));
      }
    }
    if (mounted) setState(() => _startingChat = false);
  }

  void _showReportModal() {
    String reason = 'FRAUD';
    final descCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text("Report Listing", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.red)),
                SizedBox(height: 8),
                Text("Help us keep NyumbaLink safe.", style: TextStyle(color: Colors.grey)),
                SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: reason,
                  decoration: InputDecoration(labelText: 'Reason', border: OutlineInputBorder()),
                  items: ['FRAUD', 'DUPLICATE', 'WRONG_INFO', 'UNAVAILABLE', 'OFFENSIVE']
                      .map((r) => DropdownMenuItem(value: r, child: Text(r.replace('_', ' ')))).toList(),
                  onChanged: (val) => setModalState(() => reason = val!),
                ),
                SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: InputDecoration(labelText: 'Details (Optional)', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () async {
                    try {
                      await ApiClient.submitReport(widget.listingId, reason, descCtrl.text);
                      if (mounted) {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Report submitted. Thank you.")));
                      }
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit report")));
                    }
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red, minimumSize: Size(double.infinity, 50)),
                  child: Text("Submit Report"),
                ),
                SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text("Property Details"), 
        backgroundColor: Color(0xFF059669),
        actions: [
          IconButton(
            icon: Icon(_isSaved ? Icons.favorite : Icons.favorite_border, color: _isSaved ? Colors.red : Colors.white),
            onPressed: auth.user == null ? null : _toggleSave,
          )
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _listingFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: Text("Error loading property details"));

          final listing = snapshot.data!;
          final mediaList = listing['media'] as List<dynamic>? ?? [];

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (mediaList.isNotEmpty)
                  Stack(
                    children: [
                      SizedBox(
                        height: 300,
                        child: PageView.builder(
                          onPageChanged: (index) => setState(() => _currentImageIndex = index),
                          itemCount: mediaList.length,
                          itemBuilder: (context, index) => CachedNetworkImage(
                            imageUrl: _getFullImageUrl(mediaList[index]['file']),
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorWidget: (context, url, error) => Container(color: Colors.grey[200], child: Icon(Icons.broken_image, size: 50, color: Colors.grey)),
                          ),
                        ),
                      ),
                      if (mediaList.length > 1)
                        Positioned(
                          bottom: 12, left: 0, right: 0,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: List.generate(mediaList.length, (index) {
                              return AnimatedContainer(
                                duration: Duration(milliseconds: 300),
                                margin: EdgeInsets.symmetric(horizontal: 4),
                                width: _currentImageIndex == index ? 20 : 8,
                                height: 8,
                                decoration: BoxDecoration(color: _currentImageIndex == index ? Color(0xFF059669) : Colors.white.withOpacity(0.6), borderRadius: BorderRadius.circular(4)),
                              );
                            }),
                          ),
                        ),
                    ],
                  ),
                
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(listing['title'], style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      Text("${listing['property_summary']['neighbourhood']} · ${listing['property_summary']['property_type']}", style: TextStyle(fontSize: 16, color: Colors.grey[600])),
                      SizedBox(height: 16),
                      Text("${listing['currency']} ${listing['price']}", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFF059669))),
                      Divider(height: 32),
                      Text("Description", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      Text(listing['description'] ?? "No description provided.", style: TextStyle(fontSize: 16, height: 1.5)),
                      Divider(height: 32),

                      // Landlord Info Row
                      GestureDetector(
                        onTap: () {
                          Navigator.push(context, MaterialPageRoute(
                            builder: (_) => LandlordProfileScreen(
                              landlordId: listing['created_by'],
                              landlordEmail: listing['created_by_email'] ?? '',
                            )
                          ));
                        },
                        child: Container(
                          padding: EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.grey[50], borderRadius: BorderRadius.circular(8), border: Border.all(color: Colors.grey[300]!)),
                          child: Row(
                            children: [
                              CircleAvatar(backgroundColor: Color(0xFF059669), child: Icon(Icons.person, color: Colors.white)),
                              SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text("Advertised by", style: TextStyle(fontSize: 12, color: Colors.grey[600])),
                                    Text(listing['created_by_email'] ?? 'Landlord', style: TextStyle(fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                              Icon(Icons.chevron_right, color: Colors.grey),
                            ],
                          ),
                      ),
                      SizedBox(height: 4),
                      Center(
                        child: TextButton.icon(
                          onPressed: _showReportModal,
                          icon: Icon(Icons.flag, color: Colors.red, size: 16),
                          label: Text("Report this listing", style: TextStyle(color: Colors.red, fontSize: 12)),
                        ),
                      ),
                        ),
                      ),
                      SizedBox(height: 24),
                      
                      if (auth.user == null)
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton.icon(
                            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                            icon: Icon(Icons.lock_outline),
                            label: Text("Log in to Contact Landlord"),
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.grey[800], shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                          ),
                        )
                      else
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (_isUnlocked) ...[
                              Container(
                                padding: EdgeInsets.all(16),
                                decoration: BoxDecoration(color: Colors.green[50], border: Border.all(color: Colors.green), borderRadius: BorderRadius.circular(8)),
                                child: Column(
                                  children: [
                                    Text("Contact Details Unlocked", style: TextStyle(fontWeight: FontWeight.bold, color: Colors.green[800])),
                                    SizedBox(height: 8),
                                    Text("+260 97 123 4567", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                              SizedBox(height: 12),
                            ] else ...[
                              ElevatedButton.icon(
                                onPressed: _isUnlocking ? null : () {
                                  showModalBottomSheet(
                                    context: context,
                                    isScrollControlled: true,
                                    builder: (context) => _PaymentModal(
                                      listingId: listing['id'],
                                      onSuccess: () {
                                        setState(() => _isUnlocked = true);
                                      },
                                    ),
                                  );
                                },
                                icon: _isUnlocking ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.lock_open),
                                label: Text(_isUnlocking ? "Unlocking..." : "Unlock Contact (K5 Platform Fee)"),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.orange[700], 
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  minimumSize: Size(double.infinity, 50),
                                ),
                              ),
                              SizedBox(height: 12),
                            ],

                            ElevatedButton.icon(
                              onPressed: _startingChat ? null : () => _startChat(listing['id'], listing['created_by_email']),
                              icon: _startingChat ? SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Icon(Icons.message),
                              label: Text(_startingChat ? "Opening Chat..." : "Message Landlord"),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Color(0xFF059669), 
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                minimumSize: Size(double.infinity, 50),
                              ),
                            ),
                            SizedBox(height: 12),
                            
                            // NEW: Apply & Sign Lease Button
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
                            SizedBox(height: 12),
                            
                            // THE SMART VIEWING BUTTON
                            if (_viewingStatus == 'APPROVED')
                              Container(
                                height: 50,
                                decoration: BoxDecoration(
                                  color: Colors.green[50],
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Colors.green),
                                ),
                                child: Center(child: Text("✓ Viewing Approved", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                              )
                            else if (_viewingStatus == 'PENDING')
                              Container(
                                height: 50,
                                decoration: BoxDecoration(
                                  color: Colors.orange[50],
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: Colors.orange),
                                ),
                                child: Center(child: Text("Viewing Requested (Pending)", style: TextStyle(color: Colors.orange[800], fontWeight: FontWeight.bold))),
                              )
                            else
                              OutlinedButton.icon(
                                onPressed: () async {
                                  final date = await showDatePicker(
                                    context: context,
                                    initialDate: DateTime.now().add(Duration(days: 1)),
                                    firstDate: DateTime.now(),
                                    lastDate: DateTime.now().add(Duration(days: 30)),
                                  );
                                  if (date != null) {
                                    try {
                                      await ApiClient.requestViewing(listing['id'], date.toIso8601String());
                                      setState(() => _viewingStatus = 'PENDING'); // Instantly update UI
                                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Viewing requested!")));
                                    } catch (e) {
                                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to request viewing")));
                                    }
                                  }
                                },
                                icon: Icon(Icons.calendar_today, color: Color(0xFF059669)),
                                label: Text("Request Viewing", style: TextStyle(color: Color(0xFF059669))),
                                style: OutlinedButton.styleFrom(
                                  side: BorderSide(color: Color(0xFF059669)),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  minimumSize: Size(double.infinity, 50),
                                ),
                              ),
                          ]
                        ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}


class _PaymentModal extends StatefulWidget {
  final String listingId;
  final VoidCallback onSuccess;

  _PaymentModal({required this.listingId, required this.onSuccess});

  @override
  _PaymentModalState createState() => _PaymentModalState();
}

class _PaymentModalState extends State<_PaymentModal> {
  String _provider = 'MTN';
  final _phoneCtrl = TextEditingController();
  bool _isProcessing = false;

  void _pay() async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.unlockListing(widget.listingId, _provider, _phoneCtrl.text);
      if (mounted) {
        Navigator.pop(context);
        widget.onSuccess();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment Successful! Contact Unlocked.")));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  void _showReportModal() {
    String reason = 'FRAUD';
    final descCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text("Report Listing", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.red)),
                SizedBox(height: 8),
                Text("Help us keep NyumbaLink safe.", style: TextStyle(color: Colors.grey)),
                SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: reason,
                  decoration: InputDecoration(labelText: 'Reason', border: OutlineInputBorder()),
                  items: ['FRAUD', 'DUPLICATE', 'WRONG_INFO', 'UNAVAILABLE', 'OFFENSIVE']
                      .map((r) => DropdownMenuItem(value: r, child: Text(r.replace('_', ' ')))).toList(),
                  onChanged: (val) => setModalState(() => reason = val!),
                ),
                SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: InputDecoration(labelText: 'Details (Optional)', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () async {
                    try {
                      await ApiClient.submitReport(widget.listingId, reason, descCtrl.text);
                      if (mounted) {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Report submitted. Thank you.")));
                      }
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit report")));
                    }
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red, minimumSize: Size(double.infinity, 50)),
                  child: Text("Submit Report"),
                ),
                SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text("Pay to Unlock", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Text("A K5 fee is required to reveal the landlord's contact details. This payment goes directly to the landlord.", style: TextStyle(color: Colors.grey)),
          SizedBox(height: 24),
          DropdownButtonFormField<String>(
            value: _provider,
            decoration: InputDecoration(labelText: 'Mobile Money Provider', border: OutlineInputBorder()),
            items: [
              DropdownMenuItem(value: 'MTN', child: Text("MTN MoMo")),
              DropdownMenuItem(value: 'AIRTEL', child: Text("Airtel Money")),
              DropdownMenuItem(value: 'ZAMTEL', child: Text("Zamtel Kwacha")),
            ],
            onChanged: (val) => setState(() => _provider = val!),
          ),
          SizedBox(height: 16),
          TextField(
            controller: _phoneCtrl,
            decoration: InputDecoration(labelText: 'Your Mobile Money Number', border: OutlineInputBorder(), hintText: "e.g. 0977123456"),
            keyboardType: TextInputType.phone,
          ),
          SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isProcessing || _phoneCtrl.text.isEmpty ? null : _pay,
            style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669), minimumSize: Size(double.infinity, 50)),
            child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Pay K5 via $_provider"),
          ),
          SizedBox(height: 16),
        ],
      ),
    );
  }
}


class _RentPaymentModal extends StatefulWidget {
  final String listingId;
  final double amount;

  _RentPaymentModal({required this.listingId, required this.amount});

  @override
  _RentPaymentModalState createState() => _RentPaymentModalState();
}

class _RentPaymentModalState extends State<_RentPaymentModal> {
  String _paymentType = 'RENT';
  String _provider = 'MTN';
  final _phoneCtrl = TextEditingController();
  bool _isProcessing = false;

  void _pay() async {
    setState(() => _isProcessing = true);
    try {
      await ApiClient.payRent(widget.listingId, widget.amount, _paymentType, _phoneCtrl.text);
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Payment Successful! Routed directly to Landlord.")));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
    if (mounted) setState(() => _isProcessing = false);
  }

  void _showReportModal() {
    String reason = 'FRAUD';
    final descCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) {
          return Padding(
            padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text("Report Listing", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.red)),
                SizedBox(height: 8),
                Text("Help us keep NyumbaLink safe.", style: TextStyle(color: Colors.grey)),
                SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: reason,
                  decoration: InputDecoration(labelText: 'Reason', border: OutlineInputBorder()),
                  items: ['FRAUD', 'DUPLICATE', 'WRONG_INFO', 'UNAVAILABLE', 'OFFENSIVE']
                      .map((r) => DropdownMenuItem(value: r, child: Text(r.replace('_', ' ')))).toList(),
                  onChanged: (val) => setModalState(() => reason = val!),
                ),
                SizedBox(height: 12),
                TextField(
                  controller: descCtrl,
                  decoration: InputDecoration(labelText: 'Details (Optional)', border: OutlineInputBorder()),
                  maxLines: 2,
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () async {
                    try {
                      await ApiClient.submitReport(widget.listingId, reason, descCtrl.text);
                      if (mounted) {
                        Navigator.pop(context);
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Report submitted. Thank you.")));
                      }
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit report")));
                    }
                  },
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red, minimumSize: Size(double.infinity, 50)),
                  child: Text("Submit Report"),
                ),
                SizedBox(height: 16),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom, left: 16, right: 16, top: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text("Pay to Landlord", style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Text("This payment goes directly to the landlord's Mobile Money account.", style: TextStyle(color: Colors.grey)),
          SizedBox(height: 24),
          DropdownButtonFormField<String>(
            value: _paymentType,
            decoration: InputDecoration(labelText: 'Payment Type', border: OutlineInputBorder()),
            items: [
              DropdownMenuItem(value: 'RENT', child: Text("Monthly Rent (K${widget.amount})")),
              DropdownMenuItem(value: 'DEPOSIT', child: Text("Security Deposit (K${widget.amount * 2})")),
            ],
            onChanged: (val) => setState(() => _paymentType = val!),
          ),
          SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _provider,
            decoration: InputDecoration(labelText: 'Mobile Money Provider', border: OutlineInputBorder()),
            items: [
              DropdownMenuItem(value: 'MTN', child: Text("MTN MoMo")),
              DropdownMenuItem(value: 'AIRTEL', child: Text("Airtel Money")),
              DropdownMenuItem(value: 'ZAMTEL', child: Text("Zamtel Kwacha")),
            ],
            onChanged: (val) => setState(() => _provider = val!),
          ),
          SizedBox(height: 16),
          TextField(
            controller: _phoneCtrl,
            decoration: InputDecoration(labelText: 'Your Mobile Money Number', border: OutlineInputBorder(), hintText: "e.g. 0977123456"),
            keyboardType: TextInputType.phone,
          ),
          SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isProcessing || _phoneCtrl.text.isEmpty ? null : _pay,
            style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700], minimumSize: Size(double.infinity, 50)),
            child: _isProcessing ? CircularProgressIndicator(color: Colors.white) : Text("Pay via $_provider"),
          ),
          SizedBox(height: 16),
        ],
      ),
    );
  }
}
