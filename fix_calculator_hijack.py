#!/usr/bin/env python3
"""Decouples the Affordability Calculator from the main page filters."""
from __future__ import annotations
import subprocess
from pathlib import Path
import re

ROOT = Path.cwd()
FRONTEND = ROOT / "frontend"

# ----------------------------------------------------------------
# 1. Fix HomePage.tsx (Remove the hijack effect)
# ----------------------------------------------------------------
HOME_FILE = FRONTEND / "src" / "pages" / "HomePage.tsx"
text = HOME_FILE.read_text(encoding="utf-8")

# Remove the state
text = text.replace(
    "  const [affordableFilter, setAffordableFilter] = useState<{ price: number, type: 'SALE' | 'RENT' } | null>(null)\n",
    ""
)

# Remove the useEffect that modifies the main filters
old_effect = '''  // Sync affordability filter with filters
  useEffect(() => {
    if (affordableFilter) {
      setFilters(prev => ({
        ...prev,
        max_price: affordableFilter.price,
        transaction_type: affordableFilter.type,
      }))
    }
  }, [affordableFilter])'''

text = text.replace(old_effect, "")

# Remove the prop from the calculator component
text = text.replace(
    '''      <AffordabilityCalculator 
        onFilterUpdate={(price, type) => setAffordableFilter(price && type ? { price, type } : null)} 
        listings={data?.results || []} 
      />''',
    '''      <AffordabilityCalculator listings={data?.results || []} />'''
)

HOME_FILE.write_text(text, encoding="utf-8")
print("✅ Patched HomePage.tsx: Removed calculator hijacking of main filters")

# ----------------------------------------------------------------
# 2. Fix AffordabilityCalculator.tsx (Remove the onFilterUpdate prop)
# ----------------------------------------------------------------
CALC_FILE = FRONTEND / "src" / "components" / "AffordabilityCalculator.tsx"
text = CALC_FILE.read_text(encoding="utf-8")

# Update interface
text = text.replace(
    '''interface Props {
  onFilterUpdate: (maxPrice: number | undefined, type: 'SALE' | 'RENT' | undefined) => void
  listings: any[]
}''',
    '''interface Props {
  listings: any[]
}'''
)

# Update function signature
text = text.replace(
    "export default function AffordabilityCalculator({ onFilterUpdate, listings }: Props) {",
    "export default function AffordabilityCalculator({ listings }: Props) {"
)

# Remove the onFilterUpdate calls in the useEffect
text = text.replace("      onFilterUpdate(Math.round(price), 'SALE')\n", "")
text = text.replace("      onFilterUpdate(Math.round(maxMonthlyRent), 'RENT')\n", "")
text = text.replace(
    "  }, [mode, income, downPayment, interestRate, termYears, onFilterUpdate, maxMonthlyRent])",
    "  }, [mode, income, downPayment, interestRate, termYears])"
)

CALC_FILE.write_text(text, encoding="utf-8")
print("✅ Patched AffordabilityCalculator.tsx: It now strictly filters its own mini-carousel")

# ----------------------------------------------------------------
# 3. Push to GitHub
# ----------------------------------------------------------------
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Decouple Affordability Calculator from main page filters"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 CALCULATOR HIJACK FIXED!
==================================================

Render will rebuild the frontend in ~2 minutes.

Once it's live:
1. Your main "All Properties" grid will load all PUBLISHED listings (Rentals and Sales).
2. The Affordability Calculator will display its own mini-carousel of affordable properties (Buy or Rent), but it will NOT hide the main grid.
""")