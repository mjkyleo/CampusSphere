import React, { useState, useEffect, useRef } from 'react';
import { api, formatPrice } from '../services/api.ts';
import { useWebSocket } from '../hooks/useWebSocket.ts';
import { ConversationOut, MessageOut, MessageType, ItemOut } from '../types.ts';
import { useAuth } from '../context/AuthContext.tsx';
import { useToast } from '../context/ToastContext.tsx';
import {
  MessageSquare, Send, CheckCheck, Clock, ShoppingBag,
  User, ShieldAlert, ArrowLeft, Tag, Info, Wifi, WifiOff
} from 'lucide-react';

const MessageCenter: React.FC = () => {
  const { user, refreshUnread, openReport } = useAuth();
  const { success, error } = useToast();
  const { isConnected, sendMessage: wsSendMessage, onMessage } = useWebSocket();
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [inputContent, setInputContent] = useState('');
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // 历史消息分页（上拉/滚到顶部加载更早消息）
  const HISTORY_PAGE_SIZE = 30;
  const [historyPage, setHistoryPage] = useState(1);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Track the active conversation ID in a ref so the WebSocket message
  // handler always sees the latest value without re-subscribing.
  const activeConvIdRef = useRef<string | null>(null);
  activeConvIdRef.current = activeConvId;

  // ---- Fetch conversation list on mount ----
  const fetchConversations = async () => {
    try {
      const res = await api.messages.conversations();
      if (res.code === 0 && res.data) {
        setConversations(res.data);
        if (!activeConvId && res.data.length > 0) {
          setActiveConvId(res.data[0].id);
        }
      }
    } catch {
      // Handled by mock fallback engine
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  // ---- Load message history when a conversation is selected ----
  useEffect(() => {
    if (!activeConvId) return;
    let cancelled = false;

    const loadInitial = async () => {
      setLoading(true);
      try {
        const res = await api.messages.history(activeConvId, 1, HISTORY_PAGE_SIZE);
        if (cancelled) return;
        if (res.code === 0 && res.data) {
          // 后端按时间倒序返回，反转成「旧→新」便于按聊天正常顺序渲染
          const items = [...(res.data.items || [])].reverse();
          setMessages(items);
          const total = res.data.total || 0;
          setHistoryPage(1);
          setHasMoreHistory(total > HISTORY_PAGE_SIZE);
          // 初始定位到底部（最新消息），并标记已读
          requestAnimationFrame(() => {
            const el = scrollContainerRef.current;
            if (el) el.scrollTop = el.scrollHeight;
          });
          await api.messages.read(activeConvId);
          refreshUnread();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadInitial();
    return () => {
      cancelled = true;
    };
  }, [activeConvId, refreshUnread]);

  // ---- Load older messages (滚到顶部触发，定位在更早的历史) ----
  const loadOlderHistory = async () => {
    if (!activeConvId || loadingHistory || !hasMoreHistory) return;
    setLoadingHistory(true);
    const el = scrollContainerRef.current;
    const prevScrollHeight = el?.scrollHeight ?? 0;
    const nextPage = historyPage + 1;
    try {
      const res = await api.messages.history(activeConvId, nextPage, HISTORY_PAGE_SIZE);
      if (res.code === 0 && res.data) {
        const older = [...(res.data.items || [])].reverse();
        skipAutoScrollRef.current = true; // 顶部插入，不要自动滚到底部
        setMessages((prev) => [...older, ...prev]);
        setHistoryPage(nextPage);
        const total = res.data.total || 0;
        setHasMoreHistory(nextPage * HISTORY_PAGE_SIZE < total);
        // 保持视口位置：把因顶部插入内容而增加的滚动高度补偿回去
        requestAnimationFrame(() => {
          if (el) el.scrollTop = el.scrollHeight - prevScrollHeight;
        });
      }
    } catch {
      // 忽略加载失败
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleMessagesScroll = () => {
    const el = scrollContainerRef.current;
    if (!el) return;
    if (el.scrollTop < 40 && hasMoreHistory && !loadingHistory) {
      loadOlderHistory();
    }
  };

  // ---- Subscribe to incoming WebSocket messages ----
  // The onMessage callback from useWebSocket is stable (useCallback),
  // so this effect only runs once on mount.
  useEffect(() => {
    const unsubscribe = onMessage((data: MessageOut) => {
      if (!data) return;
      const activeId = activeConvIdRef.current;

      // If the message belongs to the active conversation, append it
      // (with dedup guard in case the server echoes back our own message).
      if (activeId && data.conversation_id === activeId) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === data.id)) return prev;
          return [...prev, data];
        });
      }

      // Always update the conversation list so the latest message
      // and unread badge reflect the new message.
      setConversations((prev) => {
        const conv = prev.find((c) => c.id === data.conversation_id);
        if (!conv) return prev;
        const isActive = data.conversation_id === activeId;
        return prev.map((c) =>
          c.id === data.conversation_id
            ? {
                ...c,
                last_message: data,
                updated_at: data.created_at,
                unread_count: isActive ? 0 : (c.unread_count || 0) + 1
              }
            : c
        );
      });
    });

    return unsubscribe;
  }, [onMessage]);

  // ---- Auto-scroll to bottom on new messages ----
  // 加载更早历史（顶部插入）时置位 skipAutoScrollRef，避免被强制拉回底部
  const skipAutoScrollRef = useRef(false);
  useEffect(() => {
    if (skipAutoScrollRef.current) {
      skipAutoScrollRef.current = false;
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const activeConversation = conversations.find((c) => c.id === activeConvId);

  // ---- Send message via WebSocket ----
  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputContent.trim() || !activeConvId) return;

    const tempContent = inputContent.trim();

    // Attempt to send via WebSocket; if the connection is not open,
    // show an error and keep the input text so the user can retry.
    const sent = wsSendMessage(tempContent, activeConvId, MessageType.Text);
    if (!sent) {
      error('实时连接未建立，消息未发送。请稍后重试。');
      return;
    }

    // Sent successfully — clear the input
    setInputContent('');

    // Optimistic UI update: append our own message immediately
    const newMsg: MessageOut = {
      id: 'msg-' + Date.now(),
      conversation_id: activeConvId,
      sender_id: user?.id || 'usr-001',
      sender_nickname: user?.nickname || '我',
      sender_avatar: user?.avatar || undefined,
      type: MessageType.Text,
      content: tempContent,
      is_read: false,
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, newMsg]);

    // Update conversation list — move to top with new last_message
    setConversations((prev) => {
      const idx = prev.findIndex((c) => c.id === activeConvId);
      if (idx === -1) return prev;
      const updated = {
        ...prev[idx],
        last_message: newMsg,
        updated_at: newMsg.created_at
      };
      return [updated, ...prev.filter((_, i) => i !== idx)];
    });
  };

  const sendQuickReply = (text: string) => {
    setInputContent(text);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
            <MessageSquare className="w-8 h-8 text-indigo-600" />
            消息与交易协商
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            支持实时单聊与二手交易会话撮合，保障双方信息透明与安全
          </p>
        </div>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden grid grid-cols-1 md:grid-cols-12 min-h-[640px]">
        {/* Left: Conversation List */}
        <div className={`md:col-span-4 border-r border-slate-100 flex flex-col ${activeConvId ? 'hidden md:flex' : 'flex'}`}>
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <span className="font-bold text-slate-800 text-sm">会话列表 ({conversations.length})</span>
            <span className="text-xs text-indigo-600 font-medium">双向加密</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
            {conversations.length === 0 ? (
              <div className="p-8 text-center text-slate-400 space-y-2">
                <MessageSquare className="w-10 h-10 mx-auto stroke-1 text-slate-300" />
                <p className="text-sm">暂无活跃会话</p>
                <p className="text-xs">在二手市集或找搭子发起咨询后将在此显示</p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = conv.id === activeConvId;
                return (
                  <button
                    key={conv.id}
                    // E2E 定位锚点：列表项文案（昵称/标题）会随数据变化，
                    // 用稳定标识避免选择器依赖展示文案
                    data-testid="conversation-item"
                    onClick={() => setActiveConvId(conv.id)}
                    className={`w-full p-4 text-left flex items-start gap-3 transition-colors ${
                      isActive ? 'bg-indigo-50/80 border-r-4 border-indigo-600' : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="relative shrink-0">
                      <div className="w-12 h-12 rounded-2xl overflow-hidden bg-slate-100 border border-slate-200">
                        {conv.target_user?.avatar ? (
                          <img src={conv.target_user.avatar} alt="avatar" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-indigo-600 font-bold">
                            {conv.target_user?.nickname?.charAt(0) || 'U'}
                          </div>
                        )}
                      </div>
                      {(conv.unread_count || 0) > 0 && (
                        <span className="absolute -top-1 -right-1 px-1.5 py-0.5 bg-rose-500 text-white text-[10px] font-bold rounded-full border-2 border-white">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-slate-900 text-sm truncate">
                          {conv.target_user?.nickname || '校园用户'}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {conv.updated_at ? new Date(conv.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>

                      {conv.related_item && (
                        <div className="flex items-center gap-1 text-xs text-indigo-600 font-medium mb-1 truncate bg-indigo-50/60 px-1.5 py-0.5 rounded">
                          <Tag className="w-3 h-3 shrink-0" />
                          <span className="truncate">{conv.related_item.title}</span>
                          <span className="shrink-0 font-bold">¥{formatPrice(conv.related_item.price)}</span>
                        </div>
                      )}

                      <p className="text-xs text-slate-500 truncate">
                        {conv.last_message?.content || '点击查看聊天记录'}
                      </p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Active Chat Area */}
        <div className={`md:col-span-8 flex flex-col ${!activeConvId ? 'hidden md:flex' : 'flex'}`}>
          {activeConversation ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-white">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setActiveConvId(null)}
                    className="md:hidden p-1.5 rounded-lg hover:bg-slate-100 text-slate-600"
                  >
                    <ArrowLeft className="w-5 h-5" />
                  </button>
                  <div className="w-10 h-10 rounded-xl overflow-hidden bg-slate-100 border border-slate-200">
                    <img
                      src={activeConversation.target_user?.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'}
                      alt="avatar"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">
                      {activeConversation.target_user?.nickname || '校园卖家/买家'}
                    </h3>
                    <p className={`text-xs flex items-center gap-1 font-medium ${isConnected ? 'text-emerald-600' : 'text-slate-400'}`}>
                      {isConnected ? (
                        <>
                          <Wifi className="w-3 h-3" />
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                          在线可沟通
                        </>
                      ) : (
                        <>
                          <WifiOff className="w-3 h-3" />
                          <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
                          正在重连...
                        </>
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      openReport(
                        'message',
                        activeConversation.id,
                        `与 ${activeConversation.target_user?.nickname} 的会话`
                      )
                    }
                    className="flex items-center gap-1 px-3 py-1.5 rounded-xl border border-rose-200 text-rose-600 text-xs font-semibold hover:bg-rose-50 transition-colors"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    举报违规
                  </button>
                </div>
              </div>

              {/* Related Item Bar if Trade Session */}
              {activeConversation.related_item && (
                <div className="px-4 py-2.5 bg-indigo-50/50 border-b border-indigo-100/60 flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg overflow-hidden bg-slate-200 shrink-0">
                      <img
                        src={activeConversation.related_item.images?.[0]?.object_key || 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=150'}
                        alt="item"
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-800 truncate">
                        {activeConversation.related_item.title}
                      </p>
                      <p className="text-xs text-indigo-700 font-black">
                        ¥ {formatPrice(activeConversation.related_item.price)}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-1.5 shrink-0">
                    <button
                      onClick={() => sendQuickReply('请问这个还能小刀一下价格吗？')}
                      className="px-2.5 py-1 bg-white border border-indigo-200 text-indigo-700 rounded-lg text-xs font-semibold hover:bg-indigo-100 transition-colors"
                    >
                      申请小刀
                    </button>
                    <button
                      onClick={() => sendQuickReply('我诚心要，请问今天能在校内哪个地点当面交易验货？')}
                      className="px-2.5 py-1 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 transition-colors"
                    >
                      约面交
                    </button>
                  </div>
                </div>
              )}

              {/* Messages Feed */}
              <div
                ref={scrollContainerRef}
                onScroll={handleMessagesScroll}
                className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4 bg-slate-50/40"
              >
                {hasMoreHistory && (
                  <div className="text-center py-1">
                    {loadingHistory ? (
                      <span className="text-[10px] font-bold text-slate-400 inline-flex items-center gap-1">
                        <span className="w-3 h-3 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" />
                        正在加载更早消息...
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold text-slate-300">上滑加载更早消息</span>
                    )}
                  </div>
                )}
                <div className="text-center my-2">
                  <span className="text-[10px] font-bold text-slate-400 bg-slate-200/60 px-3 py-1 rounded-full uppercase tracking-wider">
                    会话建立安全加密通道 · 建议校内公共场所面交
                  </span>
                </div>

                {messages.map((msg) => {
                  const isMe = msg.sender_id === (user?.id || 'usr-001');
                  return (
                    <div key={msg.id} className={`flex items-end gap-2.5 ${isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className="w-8 h-8 rounded-full overflow-hidden bg-slate-200 shrink-0 mb-1 border border-slate-300">
                        {isMe ? (
                          <img
                            src={user?.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80'}
                            alt="me"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <img
                            src={activeConversation.target_user?.avatar || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'}
                            alt="them"
                            className="w-full h-full object-cover"
                          />
                        )}
                      </div>

                      <div className={`max-w-[75%] space-y-1 ${isMe ? 'items-end' : 'items-start'}`}>
                        <div
                          className={`p-3.5 rounded-2xl text-sm leading-relaxed ${
                            isMe
                              ? 'bg-indigo-600 text-white rounded-br-none shadow-md shadow-indigo-100'
                              : 'bg-white text-slate-800 rounded-bl-none border border-slate-200 shadow-sm'
                          }`}
                        >
                          {msg.content}
                        </div>
                        <div className={`flex items-center gap-1 text-[10px] text-slate-400 ${isMe ? 'justify-end' : 'justify-start'}`}>
                          <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          {isMe && <CheckCheck className="w-3 h-3 text-indigo-400" />}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Replies Bar */}
              <div className="px-4 py-2 bg-white border-t border-slate-100 flex gap-2 overflow-x-auto no-scrollbar">
                {['物品还在吗？', '什么时候方便在图书馆当面验货？', '支持微信/支付宝当面付吗？', '物品成色有瑕疵吗？'].map((quick) => (
                  <button
                    key={quick}
                    onClick={() => sendQuickReply(quick)}
                    className="whitespace-nowrap px-3 py-1 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-600 rounded-full text-xs transition-colors"
                  >
                    {quick}
                  </button>
                ))}
              </div>

              {/* Message Input Box */}
              <form onSubmit={handleSendMessage} className="p-4 bg-white border-t border-slate-200 flex items-center gap-3">
                <input
                  type="text"
                  value={inputContent}
                  onChange={(e) => setInputContent(e.target.value)}
                  placeholder={isConnected ? '输入消息，商讨物品细节或约定见面地点...' : '正在连接实时服务器...'}
                  className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:outline-none focus:border-indigo-500 focus:bg-white text-sm transition-all"
                />
                <button
                  type="submit"
                  disabled={!inputContent.trim() || !isConnected}
                  className="p-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-bold shadow-lg shadow-indigo-200 disabled:opacity-40 transition-all active:scale-95 shrink-0"
                >
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400 space-y-3">
              <MessageSquare className="w-12 h-12 text-slate-300 stroke-1" />
              <p className="font-semibold text-slate-600">请选择左侧会话开启沟通</p>
              <p className="text-xs">支持实时私信与二手交易在线撮合</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageCenter;
