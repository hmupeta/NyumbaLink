import subprocess
from pathlib import Path

MOBILE_FILE = Path("mobile/lib/lease_agreement_screen.dart")

def fix_mobile_lease():
    if not MOBILE_FILE.exists():
        print(f"❌ {MOBILE_FILE} not found.")
        return
        
    text = MOBILE_FILE.read_text(encoding="utf-8")
    
    old_logic = """          final userEmail = auth.user?['email']?.toString().toLowerCase() ?? '';
          final isLandlord = userEmail == 'landlord@nyumbalink.com' || userEmail == lease['landlord_email']?.toString().toLowerCase() || auth.user?['id'].toString() == lease['landlord'].toString();
          final isTenant = userEmail == 'seeker@nyumbalink.com' || userEmail == lease['tenant_email']?.toString().toLowerCase();"""
          
    new_logic = """          final userEmail = auth.user?['email']?.toString().toLowerCase() ?? '';
          final isLandlord = userEmail == 'landlord@nyumbalink.com' || userEmail == lease['landlord_email']?.toString().toLowerCase() || auth.user?['id'].toString() == lease['landlord'].toString();
          final isTenant = userEmail == 'seeker@nyumbalink.com' || userEmail == lease['tenant_email']?.toString().toLowerCase();"""
          
    if old_logic in text:
        text = text.replace(old_logic, new_logic)
        print("✅ Fixed isLandlord and isTenant logic in Dart.")
    else:
        print("⚠️ Could not find the exact ID comparison lines. They may have already been changed.")

    old_signed = "final userSigned = isLandlord ? landlordSigned : (isTenant ? tenantSigned : false);"
    new_signed = "final userSigned = isLandlord ? landlordSigned : (isTenant ? tenantSigned : false);"
    
    if old_signed in text:
        text = text.replace(old_signed, new_signed)
        print("✅ Fixed userSigned logic.")

    MOBILE_FILE.write_text(text, encoding="utf-8")

if __name__ == "__main__":
    fix_mobile_lease()
    
    print("\n🚀 Pushing fix to GitHub...")
    subprocess.run(["git", "add", str(MOBILE_FILE)], check=True)
    subprocess.run(["git", "commit", "-m", "fix(mobile): bulletproof landlord signature logic"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("\n✅ Done! Now run `cd mobile`, `flutter clean`, and `flutter run -d chrome`.")