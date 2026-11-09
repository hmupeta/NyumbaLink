import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';
import 'api_client.dart';
import 'auth_provider.dart';
import 'chat_screen.dart';
import 'login_screen.dart';

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
  
  // We keep track of isSaved locally to update the UI instantly
  bool _isSaved = false;
  bool _isSaving = false;
  String? _viewingStatus; // Tracks 'PENDING', 'APPROVED', 'REJECTED'
  bool _checkingViewing = true;

  @override
  void initState() {
    super.initState();
    // Removed the setState inside .then() to prevent crashes if screen is closed early
    _listingFuture = ApiClient.getListingDetail(widget.listingId);
  }

  String _getFullImageUrl(String url) {
    if (url.startsWith('http')) return url;
    return 'https://nyumbalink-backend-eaw2.onrender.com$url';
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
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            // Print actual error to console for debugging
            print("DETAIL ERROR: ${snapshot.error}");
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.error_outline, size: 48, color: Colors.red),
                  SizedBox(height: 16),
                  Text("Error loading property", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  Text("Please try again later.", style: TextStyle(color: Colors.grey)),
                ],
              ),
            );
          }

          final listing = snapshot.data!;
          // Set local _isSaved on first build
          if (_isSaved == false && listing['is_saved'] == true) {
            _isSaved = true;
          }

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
                      // Condition 1: Not logged in
                      if (auth.user == null)
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton.icon(
                            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LoginScreen())),
                            icon: Icon(Icons.lock_outline),
                            label: Text("Log in to Contact Landlord"),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.grey[800], 
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))
                            ),
                          ),
                        )
                      // Condition 2: Logged in, show both buttons
                      else
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
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
                            _checkingViewing 
                              ? SizedBox(height: 50, child: Center(child: CircularProgressIndicator()))
                              : _viewingStatus == 'APPROVED'
                                ? Container(
                                    height: 50,
                                    decoration: BoxDecoration(
                                      color: Colors.green[50],
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(color: Colors.green),
                                    ),
                                    child: Center(child: Text("✓ Viewing Approved", style: TextStyle(color: Colors.green[800], fontWeight: FontWeight.bold))),
                                  )
                                : _viewingStatus == 'PENDING'
                                  ? Container(
                                      height: 50,
                                      decoration: BoxDecoration(
                                        color: Colors.orange[50],
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: Colors.orange),
                                      ),
                                      child: Center(child: Text("Viewing Requested (Pending)", style: TextStyle(color: Colors.orange[800], fontWeight: FontWeight.bold))),
                                    )
                                  : OutlinedButton.icon(
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
