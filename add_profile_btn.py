#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
FILE = ROOT / "frontend" / "src" / "pages" / "DashboardPage.tsx"

if not FILE.exists():
    print("DashboardPage.tsx not found.")
    exit()

text = FILE.read_text(encoding="utf-8")

# We look for the header section with the "+ Create Listing" button
old_header = '''        <Link
          to="/dashboard/listings/new"
          className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700"
        >
          + Create Listing
        </Link>'''

new_header = '''        <div className="flex gap-3">
          <Link
            to={`/profiles/${user?.id}`}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-50 font-medium"
          >
            View My Public Profile
          </Link>
          <Link
            to="/dashboard/listings/new"
            className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 font-medium"
          >
            + Create Listing
          </Link>
        </div>'''

if "View My Public Profile" not in text:
    text = text.replace(old_header, new_header)
    FILE.write_text(text, encoding="utf-8")
    print("Successfully added 'View My Public Profile' button to Dashboard.")
else:
    print("Button already exists.")