'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface UserProfile {
  user_id: string;
  email: string;
  full_name: string | null;
  institution: string | null;
  role: string | null;
  created_at: string;
  user_permissions: {
    can_generate_worksheets: boolean;
    is_active: boolean;
    max_worksheets_per_day: number | null;
    permission_granted_at: string | null;
    notes: string | null;
  }[];
}

interface GenerationLog {
  id: string;
  generated_at: string;
  status: string;
  subject_code: string;
  topics: string[];
  questions_generated: number | null;
  error_message: string | null;
}

export default function AdminPortal() {
  const router = useRouter();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [logs, setLogs] = useState<GenerationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Modal states
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [quotaValue, setQuotaValue] = useState<number>(0);
  const [notes, setNotes] = useState<string>('');

  // Check if user is admin
  useEffect(() => {
    async function checkAdmin() {
      try {
        const response = await fetch('/api/admin/check-auth');
        
        if (!response.ok) {
          // Not authenticated or not admin
          router.push('/login');
          return;
        }
        
        const data = await response.json();
        
        if (!data.isAdmin) {
          // Show access denied message
          setError('Access Denied: Admin privileges required');
          setCheckingAuth(false);
          setTimeout(() => {
            router.push('/');
          }, 3000);
          return;
        }
        
        setIsAdmin(true);
        setCheckingAuth(false);
        // Fetch users after confirming admin
        fetchUsersData();
      } catch (err) {
        console.error('Error checking admin auth:', err);
        setError('Failed to verify admin access');
        setCheckingAuth(false);
        setTimeout(() => {
          router.push('/login');
        }, 2000);
      }
    }
    
    async function fetchUsersData() {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch('/api/admin/users');
        
        if (!response.ok) {
          throw new Error('Failed to fetch users');
        }
        
        const data = await response.json();
        setUsers(data.users || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load users');
      } finally {
        setLoading(false);
      }
    }
    
    checkAdmin();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchUsers = async () => {
    if (!isAdmin) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/admin/users');
      
      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }
      
      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const fetchUserLogs = async (userId: string) => {
    try {
      const response = await fetch(`/api/admin/logs?userId=${userId}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Error fetching logs:', err);
      setLogs([]);
    }
  };

  const handleGrantPermission = async (userId: string, email: string) => {
    setError(null);
    setSuccessMessage(null);
    
    try {
      const response = await fetch('/api/admin/grant-permission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId, notes }),
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to grant permission');
      }
      
      setSuccessMessage(`✅ Permission granted to ${email}`);
      setShowGrantModal(false);
      setNotes('');
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to grant permission');
    }
  };

  const handleRevokePermission = async (userId: string, email: string) => {
    if (!confirm(`Are you sure you want to revoke permission for ${email}?`)) {
      return;
    }
    
    setError(null);
    setSuccessMessage(null);
    
    try {
      const response = await fetch('/api/admin/revoke-permission', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to revoke permission');
      }
      
      setSuccessMessage(`✅ Permission revoked from ${email}`);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke permission');
    }
  };

  const handleSetQuota = async (userId: string, email: string) => {
    setError(null);
    setSuccessMessage(null);
    
    try {
      const response = await fetch('/api/admin/set-quota', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          userId, 
          maxPerDay: quotaValue > 0 ? quotaValue : null 
        }),
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to set quota');
      }
      
      setSuccessMessage(`✅ Quota set to ${quotaValue > 0 ? quotaValue + ' per day' : 'unlimited'} for ${email}`);
      setShowQuotaModal(false);
      setQuotaValue(0);
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set quota');
    }
  };

  const openGrantModal = (user: UserProfile) => {
    setSelectedUser(user);
    setShowGrantModal(true);
    setError(null);
    setSuccessMessage(null);
  };

  const openQuotaModal = (user: UserProfile) => {
    setSelectedUser(user);
    setQuotaValue(user.user_permissions[0]?.max_worksheets_per_day || 0);
    setShowQuotaModal(true);
    setError(null);
    setSuccessMessage(null);
  };

  const openUserDetails = (user: UserProfile) => {
    setSelectedUser(user);
    fetchUserLogs(user.user_id);
  };

  const getPermissionStatus = (user: UserProfile) => {
    if (!user.user_permissions || user.user_permissions.length === 0) {
      return { text: 'Not Configured', color: 'text-gray-400', bg: 'bg-gray-700' };
    }
    
    const perm = user.user_permissions[0];
    
    if (perm.can_generate_worksheets && perm.is_active) {
      return { text: 'Granted', color: 'text-green-400', bg: 'bg-green-900' };
    }
    
    if (!perm.can_generate_worksheets) {
      return { text: 'Denied', color: 'text-red-400', bg: 'bg-red-900' };
    }
    
    if (!perm.is_active) {
      return { text: 'Inactive', color: 'text-yellow-400', bg: 'bg-yellow-900' };
    }
    
    return { text: 'Unknown', color: 'text-gray-400', bg: 'bg-gray-700' };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Checking Auth Loading Screen */}
        {checkingAuth && (
          <div className="flex flex-col items-center justify-center min-h-[80vh]">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-white mb-6"></div>
            <h2 className="text-2xl font-bold text-white mb-2">Verifying Admin Access...</h2>
            <p className="text-gray-400">Please wait</p>
          </div>
        )}

        {/* Access Denied Screen */}
        {!checkingAuth && !isAdmin && (
          <div className="flex flex-col items-center justify-center min-h-[80vh]">
            <div className="text-8xl mb-6">🔒</div>
            <h2 className="text-4xl font-bold text-white mb-4">Access Denied</h2>
            <p className="text-xl text-gray-400 mb-2">Admin privileges required</p>
            <p className="text-gray-500">Redirecting to login...</p>
          </div>
        )}

        {/* Admin Content */}
        {!checkingAuth && isAdmin && (
          <>
            {/* Header */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h1 className="text-5xl font-bold text-white mb-2">👑 Admin Portal</h1>
                  <p className="text-gray-300">Manage user permissions and monitor activity</p>
                </div>
                <Link 
                  href="/generate"
                  className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                >
                  ← Back to App
                </Link>
              </div>
            </div>

            {/* Success/Error Messages */}
            {successMessage && (
              <div className="bg-green-900 bg-opacity-50 border border-green-500 rounded-xl p-4 mb-6">
                <p className="text-green-200">{successMessage}</p>
              </div>
            )}
            
            {error && (
              <div className="bg-red-900 bg-opacity-50 border border-red-500 rounded-xl p-4 mb-6">
                <p className="text-red-200">{error}</p>
              </div>
            )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 bg-opacity-80 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-2">👥</div>
            <div className="text-2xl font-bold text-white">{users.length}</div>
            <div className="text-sm text-gray-400">Total Users</div>
          </div>
          
          <div className="bg-gray-800 bg-opacity-80 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-2">✅</div>
            <div className="text-2xl font-bold text-green-400">
              {users.filter(u => u.user_permissions[0]?.can_generate_worksheets).length}
            </div>
            <div className="text-sm text-gray-400">Approved Users</div>
          </div>
          
          <div className="bg-gray-800 bg-opacity-80 rounded-xl p-6 border border-gray-700">
            <div className="text-3xl mb-2">⏳</div>
            <div className="text-2xl font-bold text-yellow-400">
              {users.filter(u => !u.user_permissions[0]?.can_generate_worksheets).length}
            </div>
            <div className="text-sm text-gray-400">Pending Approval</div>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-gray-800 bg-opacity-80 backdrop-blur-lg rounded-2xl shadow-xl border border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-700">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              👥 User Management
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
              <p className="text-gray-400">Loading users...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-xl text-gray-400">No users yet</p>
              <p className="text-sm text-gray-500 mt-2">Users will appear here after they sign up</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700 bg-opacity-50">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">User</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Institution</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Status</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Quota</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Joined</th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-gray-300">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {users.map((user) => {
                    const status = getPermissionStatus(user);
                    const perm = user.user_permissions[0];
                    
                    return (
                      <tr 
                        key={user.user_id} 
                        className="hover:bg-gray-700 hover:bg-opacity-30 transition-colors cursor-pointer"
                        onClick={() => openUserDetails(user)}
                      >
                        <td className="px-6 py-4">
                          <div>
                            <div className="font-semibold text-white">{user.email}</div>
                            {user.full_name && (
                              <div className="text-sm text-gray-400">{user.full_name}</div>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-gray-300">
                          {user.institution || <span className="text-gray-500">-</span>}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${status.bg} ${status.color}`}>
                            {status.text}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-gray-300">
                          {perm?.max_worksheets_per_day 
                            ? `${perm.max_worksheets_per_day}/day` 
                            : <span className="text-gray-500">Unlimited</span>
                          }
                        </td>
                        <td className="px-6 py-4 text-gray-400 text-sm">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex gap-2 justify-end">
                            {perm?.can_generate_worksheets ? (
                              <button
                                onClick={() => handleRevokePermission(user.user_id, user.email)}
                                className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
                              >
                                Revoke
                              </button>
                            ) : (
                              <button
                                onClick={() => openGrantModal(user)}
                                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                              >
                                Grant
                              </button>
                            )}
                            <button
                              onClick={() => openQuotaModal(user)}
                              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                            >
                              Set Quota
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Grant Permission Modal */}
        {showGrantModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full border border-gray-700">
              <h3 className="text-2xl font-bold text-white mb-4">Grant Permission</h3>
              <p className="text-gray-300 mb-6">
                Grant worksheet generation permission to <strong>{selectedUser.email}</strong>?
              </p>
              
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Admin Notes (Optional)
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g., Approved for school project"
                  className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
                  rows={3}
                />
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => handleGrantPermission(selectedUser.user_id, selectedUser.email)}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold transition-colors"
                >
                  ✅ Grant Permission
                </button>
                <button
                  onClick={() => {
                    setShowGrantModal(false);
                    setNotes('');
                  }}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg font-semibold transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Set Quota Modal */}
        {showQuotaModal && selectedUser && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-2xl p-8 max-w-md w-full border border-gray-700">
              <h3 className="text-2xl font-bold text-white mb-4">Set Daily Quota</h3>
              <p className="text-gray-300 mb-6">
                Set daily worksheet generation limit for <strong>{selectedUser.email}</strong>
              </p>
              
              <div className="mb-6">
                <label className="block text-sm font-semibold text-gray-300 mb-2">
                  Max Worksheets Per Day (0 = Unlimited)
                </label>
                <input
                  type="number"
                  value={quotaValue}
                  onChange={(e) => setQuotaValue(parseInt(e.target.value) || 0)}
                  min="0"
                  max="100"
                  className="w-full p-3 border-2 border-gray-600 bg-gray-700 text-white rounded-lg focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={() => handleSetQuota(selectedUser.user_id, selectedUser.email)}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors"
                >
                  💾 Save Quota
                </button>
                <button
                  onClick={() => {
                    setShowQuotaModal(false);
                    setQuotaValue(0);
                  }}
                  className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-3 rounded-lg font-semibold transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* User Details Modal */}
        {selectedUser && !showGrantModal && !showQuotaModal && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedUser(null)}
          >
            <div 
              className="bg-gray-800 rounded-2xl p-8 max-w-4xl w-full border border-gray-700 max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-white mb-1">{selectedUser.email}</h3>
                  {selectedUser.full_name && (
                    <p className="text-gray-400">{selectedUser.full_name}</p>
                  )}
                </div>
                <button
                  onClick={() => setSelectedUser(null)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              {/* User Info */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-700 bg-opacity-50 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">Institution</div>
                  <div className="text-white font-semibold">
                    {selectedUser.institution || 'Not specified'}
                  </div>
                </div>
                <div className="bg-gray-700 bg-opacity-50 rounded-lg p-4">
                  <div className="text-sm text-gray-400 mb-1">Role</div>
                  <div className="text-white font-semibold">
                    {selectedUser.role || 'Not specified'}
                  </div>
                </div>
              </div>

              {/* Generation Logs */}
              <h4 className="text-xl font-bold text-white mb-4">📊 Generation History</h4>
              {logs.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No generation history yet</p>
              ) : (
                <div className="space-y-3">
                  {logs.map((log) => (
                    <div key={log.id} className="bg-gray-700 bg-opacity-50 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-2xl ${log.status === 'success' ? '✅' : '❌'}`}>
                            {log.status === 'success' ? '✅' : '❌'}
                          </span>
                          <span className="font-semibold text-white">{log.subject_code}</span>
                        </div>
                        <span className="text-sm text-gray-400">
                          {new Date(log.generated_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-sm text-gray-300">
                        Topics: {log.topics.join(', ')} • {log.questions_generated || 0} questions
                      </div>
                      {log.error_message && (
                        <div className="text-sm text-red-400 mt-2">
                          Error: {log.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        </>
        )}
      </div>
    </div>
  );
}
