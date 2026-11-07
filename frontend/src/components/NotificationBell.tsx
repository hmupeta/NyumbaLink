import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/notifications'

export default function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data: unreadData } = useQuery({
    queryKey: ['notifications-unread'],
    queryFn: notificationsApi.unreadCount,
    refetchInterval: 10000 // Poll every 10s
  })

  const { data: listData } = useQuery({
    queryKey: ['notifications-list'],
    queryFn: notificationsApi.list,
    enabled: isOpen,
  })

  const markAllMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] })
    }
  })

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const unreadCount = unreadData?.count || 0

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-emerald-700 transition focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform translate-x-1/4 -translate-y-1/4 bg-red-600 rounded-full">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-100 z-50 overflow-hidden">
          <div className="flex justify-between items-center px-4 py-3 bg-gray-50 border-b">
            <h3 className="font-bold text-gray-800 text-sm">Notifications</h3>
            {unreadCount > 0 && (
              <button onClick={() => markAllMutation.mutate()} className="text-xs text-emerald-600 hover:underline">
                Mark all read
              </button>
            )}
          </div>
          
          <div className="max-h-96 overflow-y-auto">
            {!listData?.results || listData.results.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">No notifications yet.</div>
            ) : (
              listData.results.map((n: any) => (
                <Link 
                  key={n.id} 
                  to={n.link || "#"}
                  onClick={() => {
                    if (!n.is_read) {
                      notificationsApi.markRead(n.id)
                      queryClient.invalidateQueries({ queryKey: ['notifications-unread'] })
                    }
                    setIsOpen(false)
                  }}
                  className={`block px-4 py-3 border-b hover:bg-gray-50 transition ${!n.is_read ? 'bg-emerald-50/50' : ''}`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <p className={`text-sm ${!n.is_read ? 'font-bold text-gray-900' : 'font-medium text-gray-700'}`}>{n.title}</p>
                    <span className="text-[10px] text-gray-400 whitespace-nowrap ml-2">
                      {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2">{n.message}</p>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
