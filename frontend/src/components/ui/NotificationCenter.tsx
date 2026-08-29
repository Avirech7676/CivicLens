'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Bell, CheckCheck, ExternalLink, Info, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { getNotifications, getUnreadNotificationCount, markNotificationRead, markAllNotificationsRead } from '@/lib/api';
import { AppNotification } from '@/types';

function timeAgo(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'CITIZEN' | 'DISPATCHER'>('ALL');
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotificationsData = async () => {
    try {
      setLoading(true);
      const filter = activeFilter === 'ALL' ? undefined : activeFilter;
      const [notifs, unread] = await Promise.all([
        getNotifications(filter),
        getUnreadNotificationCount(filter)
      ]);
      setNotifications(notifs);
      setUnreadCount(unread.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotificationsData();
    const interval = setInterval(fetchNotificationsData, 10000); // Polling every 10 seconds for real-time operational updates
    return () => clearInterval(interval);
  }, [activeFilter]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const filter = activeFilter === 'ALL' ? undefined : activeFilter;
      await markAllNotificationsRead(filter);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err);
    }
  };

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'INCIDENT_PRIORITY_ALERT':
        return <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-red-950 text-red-400 border border-red-800">P1 Alert</span>;
      case 'VERIFICATION_REQUIRED':
        return <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-amber-950 text-amber-400 border border-amber-800">Verify</span>;
      case 'REPORT_CONSOLIDATED':
        return <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-indigo-950 text-indigo-400 border border-indigo-800">Linked</span>;
      case 'INCIDENT_VERIFIED':
        return <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-emerald-950 text-emerald-400 border border-emerald-800">Closed</span>;
      default:
        return <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-slate-800 text-slate-300 border border-slate-700">Update</span>;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition focus:outline-none focus:ring-2 focus:ring-sky-500"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-sky-500 text-[10px] font-bold text-slate-950 ring-2 ring-slate-900 animate-pulse">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl z-50 overflow-hidden text-slate-100">
          {/* Header */}
          <div className="p-3 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-sky-400" />
              <span className="font-semibold text-sm">Notifications</span>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs font-mono bg-sky-950 text-sky-400 border border-sky-800 rounded-full">
                  {unreadCount} unread
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-slate-400 hover:text-sky-400 transition flex items-center gap-1"
                title="Mark all as read"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          {/* Filter Tabs */}
          <div className="flex border-b border-slate-800 text-xs font-medium bg-slate-900/50">
            <button
              onClick={() => setActiveFilter('ALL')}
              className={`flex-1 py-2 text-center transition border-b-2 ${activeFilter === 'ALL' ? 'border-sky-500 text-sky-400 font-bold' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
            >
              All
            </button>
            <button
              onClick={() => setActiveFilter('CITIZEN')}
              className={`flex-1 py-2 text-center transition border-b-2 ${activeFilter === 'CITIZEN' ? 'border-sky-500 text-sky-400 font-bold' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
            >
              Citizen
            </button>
            <button
              onClick={() => setActiveFilter('DISPATCHER')}
              className={`flex-1 py-2 text-center transition border-b-2 ${activeFilter === 'DISPATCHER' ? 'border-sky-500 text-sky-400 font-bold' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
            >
              Dispatcher
            </button>
          </div>

          {/* Notification List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-800/60">
            {loading && notifications.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400 animate-pulse">
                Loading notification updates...
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">
                <Info className="w-6 h-6 mx-auto mb-2 text-slate-500" />
                No notifications found.
              </div>
            ) : (
              notifications.map((n) => {
                const targetUrl = n.event_type === 'VERIFICATION_REQUIRED' && n.incident_id
                  ? `/verify/${n.incident_id}`
                  : n.incident_id
                  ? `/incident/${n.incident_id}`
                  : '#';

                return (
                  <div
                    key={n.id}
                    className={`p-3 transition text-xs relative group hover:bg-slate-800/50 ${
                      !n.is_read ? 'bg-sky-950/20 border-l-2 border-sky-500' : 'bg-slate-900/40'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {getEventBadge(n.event_type)}
                        <span className="font-semibold text-slate-200">{n.title}</span>
                      </div>
                      <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                        {timeAgo(n.created_at)}
                      </span>
                    </div>

                    <p className="text-slate-300 leading-relaxed mb-2 line-clamp-2">
                      {n.message}
                    </p>

                    {/* Metadata & Actions */}
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/40">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          Channel: {n.channel}
                        </span>
                        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-950 text-sky-400 border border-sky-900">
                          Mode: {n.provider}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        {!n.is_read && (
                          <button
                            onClick={(e) => handleMarkRead(n.id, e)}
                            className="text-slate-400 hover:text-sky-400 transition"
                            title="Mark as read"
                          >
                            Mark Read
                          </button>
                        )}

                        {n.incident_id && (
                          <Link
                            href={targetUrl}
                            onClick={() => setIsOpen(false)}
                            className="text-sky-400 hover:text-sky-300 font-medium flex items-center gap-0.5"
                          >
                            <span>View</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
