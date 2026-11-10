import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'api_client.dart';

class ManageListingScreen extends StatefulWidget {
  final String listingId;
  final Function onUpdate; // Callback to refresh the dashboard

  ManageListingScreen({required this.listingId, required this.onUpdate});

  @override
  _ManageListingScreenState createState() => _ManageListingScreenState();
}

class _ManageListingScreenState extends State<ManageListingScreen> {
  late Future<Map<String, dynamic>> _listingFuture;
  final _titleCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  bool _isLoading = false;
  bool _isInitialized = false;

  @override
  void initState() {
    super.initState();
    _listingFuture = ApiClient.getListingDetail(widget.listingId).then((data) {
      // Pre-fill the form fields once data is loaded
      if (!_isInitialized) {
        _titleCtrl.text = data['title'] ?? '';
        _priceCtrl.text = data['price']?.toString() ?? '';
        _descCtrl.text = data['description'] ?? '';
        _isInitialized = true;
      }
      return data;
    });
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
  }

  void _submitForReview() async {
    setState(() => _isLoading = true);
    try {
      await ApiClient.submitListing(widget.listingId);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Listing submitted for review!")));
      widget.onUpdate(); // Refresh the dashboard
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to submit listing")));
      setState(() => _isLoading = false);
    }
  }

  void _saveChanges() async {
    setState(() => _isLoading = true);
    try {
      await ApiClient.updateListing(widget.listingId, {
        'title': _titleCtrl.text,
        'price': double.parse(_priceCtrl.text),
        'description': _descCtrl.text,
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Listing updated successfully!")));
      widget.onUpdate(); // Refresh the dashboard list
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to update listing")));
    }
    setState(() => _isLoading = false);
  }

  void _deleteListing() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text("Delete Listing?"),
        content: Text("This action cannot be undone. Are you sure you want to permanently delete this property?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text("Cancel")),
          TextButton(
            onPressed: () => Navigator.pop(context, true), 
            child: Text("Delete", style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isLoading = true);
    try {
      await ApiClient.deleteListing(widget.listingId);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Listing deleted")));
      widget.onUpdate();
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Failed to delete listing")));
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Manage Property"), backgroundColor: Color(0xFF059669)),
      body: _isLoading 
        ? Center(child: CircularProgressIndicator())
        : FutureBuilder<Map<String, dynamic>>(
            future: _listingFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) return Center(child: CircularProgressIndicator());
              if (snapshot.hasError) return Center(child: Text("Error loading details"));

              final listing = snapshot.data!;
              final mediaList = listing['media'] as List<dynamic>? ?? [];
              final coverUrl = mediaList.isNotEmpty ? mediaList[0]['file'] : null;
              final status = listing['status'] ?? 'DRAFT';

              return SingleChildScrollView(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Status Badge
                    Center(
                      child: Container(
                        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        decoration: BoxDecoration(
                          color: status == 'PUBLISHED' ? Colors.green[100] : Colors.orange[100],
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          "Status: $status",
                          style: TextStyle(
                            color: status == 'PUBLISHED' ? Colors.green[800] : Colors.orange[800],
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(height: 16),

                    // Cover Image
                    if (coverUrl != null)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: CachedNetworkImage(
                          imageUrl: _getFullImageUrl(coverUrl),
                          height: 200,
                          width: double.infinity,
                          fit: BoxFit.cover,
                        ),
                      ),
                    SizedBox(height: 24),

                    // Editable Fields
                    TextField(
                      controller: _titleCtrl,
                      decoration: InputDecoration(labelText: 'Listing Title', border: OutlineInputBorder()),
                    ),
                    SizedBox(height: 16),
                    TextField(
                      controller: _priceCtrl,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: 'Monthly Rent (ZMW)', border: OutlineInputBorder()),
                    ),
                    SizedBox(height: 16),
                    TextField(
                      controller: _descCtrl,
                      maxLines: 4,
                      decoration: InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
                    ),
                    SizedBox(height: 32),

                    // Actions
                    // Submit for Review button (only if DRAFT)
                    if (status == 'DRAFT') ...[
                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: _submitForReview,
                          style: ElevatedButton.styleFrom(backgroundColor: Colors.blue[700]),
                          child: Text("Submit for Review"),
                        ),
                      ),
                      SizedBox(height: 12),
                    ],

                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: ElevatedButton(
                        onPressed: _saveChanges,
                        style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                        child: Text("Save Changes"),
                      ),
                    ),
                    SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      height: 50,
                      child: OutlinedButton(
                        onPressed: _deleteListing,
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: Colors.red),
                          foregroundColor: Colors.red,
                        ),
                        child: Text("Delete Property"),
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
