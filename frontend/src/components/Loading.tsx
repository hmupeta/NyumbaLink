export default function Loading({ label = 'Loading…' }: { label?: string }) {
  return <div className="py-12 text-center text-gray-500">{label}</div>
}
