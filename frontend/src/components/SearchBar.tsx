import { useState, type FormEvent } from 'react'

interface Props {
  initialValue?: string
  onSearch: (value: string) => void
}

export default function SearchBar({ initialValue = '', onSearch }: Props) {
  const [value, setValue] = useState(initialValue)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(value.trim())
  }

  return (
    <form onSubmit={submit} className="flex gap-2 w-full max-w-2xl">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search by neighbourhood, description…"
        className="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />
      <button
        type="submit"
        className="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700"
      >
        Search
      </button>
    </form>
  )
}
