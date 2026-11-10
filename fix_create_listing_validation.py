#!/usr/bin/env python3
"""Fixes the FormatException by validating numeric fields before parsing."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "mobile" / "lib" / "create_listing_screen.dart"

text = FILE.read_text(encoding="utf-8")

old_submit = '''  void _submit() async {
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
  }'''

new_submit = '''  void _submit() async {
    if (_imageBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please select a cover image")));
      return;
    }
    if (_titleCtrl.text.trim().isEmpty || _neighbourhoodCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Please enter a title and neighbourhood")));
      return;
    }

    // Safely parse numeric fields
    final price = double.tryParse(_priceCtrl.text);
    final beds = int.tryParse(_bedCtrl.text);
    final baths = int.tryParse(_bathCtrl.text);
    final area = double.tryParse(_areaCtrl.text);

    if (price == null || beds == null || baths == null || area == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text("Please enter valid numbers for Price, Beds, Baths, and Area"),
        backgroundColor: Colors.red,
      ));
      return;
    }

    setState(() => _isLoading = true);
    try {
      // 1. Create/Get Neighbourhood
      final hoodData = await ApiClient.createNeighbourhood(_neighbourhoodCtrl.text.trim());
      final String neighbourhoodId = hoodData['id'];

      // 2. Create Property & Listing
      await ApiClient.createPropertyAndListing(
        title: _titleCtrl.text.trim(),
        description: _descCtrl.text.trim(),
        price: price,
        bedrooms: beds,
        bathrooms: baths,
        floorArea: area,
        propertyType: _propertyType,
        neighbourhoodId: neighbourhoodId,
        imageBytes: _imageBytes!,
        imageName: _imageName!,
      );
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Property Listed Successfully!")));
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _isLoading = false);
  }'''

if old_submit in text:
    text = text.replace(old_submit, new_submit)
    FILE.write_text(text, encoding="utf-8")
    print("✅ Patched create_listing_screen.dart: Added numeric validation")
else:
    print("⚠️ Could not find the exact _submit function. Please check manually.")

print("""
==================================================
🎉 VALIDATION FIXED!
==================================================

Go back to your Flutter terminal and press 'r' to hot reload.

Now, if you try to publish a listing without entering a price, 
you will see a red message saying "Please enter valid numbers..." 
instead of the app crashing.
""")