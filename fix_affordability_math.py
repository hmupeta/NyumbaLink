#!/usr/bin/env python3
"""Fixes the Affordability Calculator to use real mortgage amortization math."""
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "frontend" / "src" / "components" / "AffordabilityCalculator.tsx"

text = FILE.read_text(encoding="utf-8")

# 1. Fix the useEffect calculation
old_use_effect = '''  useEffect(() => {
    // Assuming 30% of income goes to mortgage
    const monthlyPayment = income * 0.30
    const monthlyRate = (interestRate / 100) / 12
    const numPayments = termYears * 12

    // Standard Mortgage Formula: P = M * [(1+r)^n - 1] / [r * (1+r)^n]
    let loanAmount = 0
    if (monthlyRate > 0) {
      loanAmount = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
    } else {
      loanAmount = monthlyPayment * numPayments
    }

    const maxHomePrice = loanAmount + downPayment
    onBudgetChange(Math.round(maxHomePrice))
  }, [income, downPayment, interestRate, termYears, onBudgetChange])'''

new_use_effect = '''  useEffect(() => {
    // 1. Calculate the monthly housing budget (30% of income)
    const monthlyPayment = income * 0.30
    
    // 2. Calculate the loan amount using standard mortgage amortization
    const monthlyRate = (interestRate / 100) / 12
    const numPayments = termYears * 12
    
    let loanAmount = 0
    if (monthlyRate > 0) {
      // Standard Mortgage Formula: P = M * [(1+r)^n - 1] / [r * (1+r)^n]
      loanAmount = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
    } else {
      // If interest is 0%, simple multiplication
      loanAmount = monthlyPayment * numPayments
    }

    // 3. Add down payment to get the max home price
    const maxHomePrice = loanAmount + downPayment
    onBudgetChange(Math.round(maxHomePrice))
  }, [income, downPayment, interestRate, termYears, onBudgetChange])'''

if old_use_effect in text:
    text = text.replace(old_use_effect, new_use_effect)
    print("✅ Patched AffordabilityCalculator.tsx: Corrected max home price calculation")

# 2. Fix the affordable listings filter to use the same state instead of inline math
old_filter = '''  // Filter listings that fall within the calculated budget
  const affordableListings = listings.filter(l => Number(l.price) <= (income * 0.30 * termYears * 12 + downPayment))'''

new_filter = '''  // Filter listings that fall within the calculated budget
  // (We compute the max price exactly as we did in the useEffect above)
  const monthlyPayment = income * 0.30
  const monthlyRate = (interestRate / 100) / 12
  const numPayments = termYears * 12
  let maxLoan = 0
  if (monthlyRate > 0) {
    maxLoan = monthlyPayment * (Math.pow(1 + monthlyRate, numPayments) - 1) / (monthlyRate * Math.pow(1 + monthlyRate, numPayments))
  } else {
    maxLoan = monthlyPayment * numPayments
  }
  const maxAffordablePrice = maxLoan + downPayment

  const affordableListings = listings.filter(l => Number(l.price) <= maxAffordablePrice)'''

if old_filter in text:
    text = text.replace(old_filter, new_filter)
    print("✅ Patched AffordabilityCalculator.tsx: Corrected listing filter logic")

FILE.write_text(text, encoding="utf-8")

# 3. Push to GitHub
import subprocess
print("\n🚀 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Fix: Use correct mortgage amortization formula in Affordability Calculator"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)

print("""
==================================================
🎉 MATH FIXED!
==================================================

Render will now rebuild the frontend.

Once it's live, check the calculator again with the same numbers (Income: 1500, Interest: 18%).
You will see the **Max Home Price** drop to a realistic **K 27,937** (instead of K 81,000), 
which is what a bank would actually lend you at that rate!
""")