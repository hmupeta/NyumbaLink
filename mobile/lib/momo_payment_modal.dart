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
        final res = await ApiClient.checkStatus('/payments/status/$_reference/');
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
