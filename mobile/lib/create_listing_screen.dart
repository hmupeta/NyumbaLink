import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'api_client.dart';

class CreateListingScreen extends StatefulWidget {
  @override
  _CreateListingScreenState createState() => _CreateListingScreenState();
}

class _CreateListingScreenState extends State<CreateListingScreen> {
  final _titleCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  final _bedCtrl = TextEditingController();
  final _bathCtrl = TextEditingController();
  final _areaCtrl = TextEditingController();
  final _neighbourhoodCtrl = TextEditingController(); // Changed to TextField
  
  String _propertyType = 'HOUSE';
  List<int>? _imageBytes;
  String? _imageName;
  bool _isLoading = false;

  void _pickImage() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(type: FileType.image, withData: true);
    if (result != null) {
      setState(() {
        _imageBytes = result.files.single.bytes;
        _imageName = result.files.single.name;
      });
    }
  }

  void _submit() async {
    if (_imageBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please select a cover image")));
      return;
    }
    if (_neighbourhoodCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please enter a neighbourhood")));
      return;
    }

    setState(() => _isLoading = true);
    try {
      // 1. Check if the neighbourhood exists, if not, create it.
      // We send the name to the backend, and it returns the ID (creating it if necessary).
      final hoodData = await ApiClient.createNeighbourhood(_neighbourhoodCtrl.text.trim());
      final String neighbourhoodId = hoodData['id'];

      // 2. Create the Property & Listing
      await ApiClient.createPropertyAndListing(
        title: _titleCtrl.text,
        description: _descCtrl.text,
        price: double.parse(_priceCtrl.text),
        bedrooms: int.parse(_bedCtrl.text),
        bathrooms: int.parse(_bathCtrl.text),
        floorArea: double.parse(_areaCtrl.text),
        propertyType: _propertyType,
        neighbourhoodId: neighbourhoodId,
        imageBytes: _imageBytes!,
        imageName: _imageName!,
      );
      
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Property Listed Successfully!")));
      Navigator.pop(context);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Create Listing"), backgroundColor: Color(0xFF059669)),
      body: _isLoading 
        ? Center(child: CircularProgressIndicator())
        : SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(controller: _titleCtrl, decoration: InputDecoration(labelText: 'Listing Title', border: OutlineInputBorder())),
                SizedBox(height: 12),
                TextField(controller: _priceCtrl, decoration: InputDecoration(labelText: 'Monthly Rent (ZMW)', border: OutlineInputBorder()), keyboardType: TextInputType.number),
                SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _propertyType,
                  decoration: InputDecoration(labelText: 'Property Type', border: OutlineInputBorder()),
                  items: ['HOUSE', 'APARTMENT', 'TOWNHOUSE', 'LAND'].map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (val) => setState(() => _propertyType = val!),
                ),
                SizedBox(height: 12),
                // Changed from Dropdown to TextField to allow custom locations
                TextField(
                  controller: _neighbourhoodCtrl,
                  decoration: InputDecoration(
                    labelText: 'Neighbourhood / Area',
                    hintText: 'e.g., Kabulonga, Ibex Hill, Meanwood',
                    border: OutlineInputBorder(),
                    suffixIcon: Icon(Icons.location_on, color: Color(0xFF059669)),
                  ),
                ),
                SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: TextField(controller: _bedCtrl, decoration: InputDecoration(labelText: 'Beds', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                    SizedBox(width: 8),
                    Expanded(child: TextField(controller: _bathCtrl, decoration: InputDecoration(labelText: 'Baths', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                    SizedBox(width: 8),
                    Expanded(child: TextField(controller: _areaCtrl, decoration: InputDecoration(labelText: 'SqM', border: OutlineInputBorder()), keyboardType: TextInputType.number)),
                  ],
                ),
                SizedBox(height: 12),
                TextField(controller: _descCtrl, decoration: InputDecoration(labelText: 'Description', border: OutlineInputBorder()), maxLines: 3),
                SizedBox(height: 20),
                GestureDetector(
                  onTap: _pickImage,
                  child: Container(
                    height: 150,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.grey[200],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey),
                    ),
                    child: _imageBytes != null 
                      ? ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(Uint8List.fromList(_imageBytes!), fit: BoxFit.cover))
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [Icon(Icons.add_a_photo, size: 40, color: Colors.grey), Text("Upload Cover Image", style: TextStyle(color: Colors.grey))],
                        ),
                  ),
                ),
                SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton(
                    onPressed: _submit,
                    style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF059669)),
                    child: Text("Publish Listing", style: TextStyle(fontSize: 16)),
                  ),
                ),
              ],
            ),
          ),
    );
  }
}
