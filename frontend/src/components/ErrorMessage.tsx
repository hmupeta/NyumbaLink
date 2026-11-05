export default function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="my-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
      {message}
    </div>
  )
}
