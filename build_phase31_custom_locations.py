#!/usr/bin/env python3
"""Allows landlords to create custom neighbourhoods on the fly."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.cwd()
MOBILE = ROOT / "mobile"
LIB = MOBILE / "lib"

# ---------------------------------------------------------------- 1. Backend: Allow Neighbourhood Creation
VIEWS_FILE = ROOT / "apps" / "locations" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "class NeighbourhoodViewSet(viewsets.ReadOnlyModelViewSet)" in text:
    text = text.replace(
        "class NeighbourhoodViewSet(viewsets.ReadOnlyModelViewSet):",
        "from rest_framework import permissions, status\nfrom rest_framework.response import Response\nfrom django.utils.text import slugify\n\nclass NeighbourhoodViewSet(viewsets.ModelViewSet):"
    )
    text = text.replace(
        '    queryset = Neighbourhood.objects.select_related("locality").order_by("name")\n    serializer_class = NeighbourhoodSerializer\n    filterset_fields = ("locality",)\n    search_fields = ("name",)\n    lookup_field = "slug"',
        '''    queryset = Neighbourhood.objects.select_related("locality").order_by("name")
    serializer_class = NeighbourhoodSerializer
    filterset_fields = ("locality",)
    search_fields = ("name",)
    lookup_field = "slug"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def create(self, request):
        name = request.data.get("name")
        if not name:
            return Response({"detail": "Name is required"}, status=400)
            
        # Check if it already exists (case-insensitive)
        existing = Neighbourhood.objects.filter(name__iexact=name).first()
        if existing:
            return Response(NeighbourhoodSerializer(existing).data, status=200)

        # If it's brand new, attach it to a default locality (e.g. Lusaka)
        from apps.locations.models import Locality
        default_locality = Locality.objects.first()
        if not default_locality:
            return Response({"detail": "No localities configured in the system."}, status=500)

        slug = slugify(name)
        # Ensure slug is unique
        original_slug = slug
        counter = 1
        while Neighbourhood.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        new_hood = Neighbourhood.objects.create(
            locality=default_locality,
            name=name,
            slug=slug
        )
        return Response(NeighbourhoodSerializer(new_hood).data, status=201)'''
    )
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched apps/locations/views.py: Allowed neighbourhood creation")

# ---------------------------------------------------------------- 2. Flutter: Update API Client
API_FILE = LIB / "api_client.dart"
text = API_FILE.read_text(encoding="utf-8")

if "createNeighbourhood" not in text:
    text = text.replace(
        "  static Future<Map<String, dynamic>> getListingDetail(String id) async {",
        '''  static Future<Map<String, dynamic>> createNeighbourhood(String name) async {
    final res = await http.post(
      Uri.parse('$baseUrl/neighbourhoods/'),
      headers: await getHeaders(),
      body: jsonEncode({'name': name}),
    );
    if (res.statusCode == 200 || res.statusCode == 201) {
      return jsonDecode(res.body);
    }
    throw Exception('Failed to create neighbourhood');
  }

  static Future<Map<String, dynamic>> getListingDetail(String id) async {'''
    )
    API_FILE.write_text(text, encoding="utf-8")
    print("✅ Patched api_client.dart: Added createNeighbourhood")

# ---------------------------------------------------------------- 3. Flutter: Update Create Listing Screen
CREATE_FILE = LIB / "create_listing_screen.dart"

NEW_CREATE_SCREEN = '''
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
'''
(CREATE_FILE).write_text(NEW_CREATE_SCREEN.strip() + "\n", encoding="utf-8")
print("✅ Patched create_listing_screen.dart: Replaced Dropdown with custom TextField")

# ---------------------------------------------------------------- 4. Push Backend Changes
print("\n🚀 Pushing backend changes to GitHub...")
subprocess.run(["git", "add", "apps/locations/views.py"], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Allow dynamic neighbourhood creation via API"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 PHASE 31 COMPLETE: CUSTOM LOCATIONS ALLOWED
==================================================

1. Render will auto-deploy the updated Django backend.
2. The Flutter UI is already updated locally.

Go back to your Flutter terminal, quit ('q'), and restart the app.

1. Go to Profile -> My Properties (Landlord) -> Click the + button.
2. Under "Neighbourhood / Area", type a completely new area (e.g., "Ibex Hill").
3. Fill in the other details and click Publish.
4. The backend will automatically create the new neighbourhood in the database and attach the property to it!
""")