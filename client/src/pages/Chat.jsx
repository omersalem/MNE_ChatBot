import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, User, RefreshCw, Trash2, Copy, Check, CornerDownLeft, StopCircle, Layers, FolderOpen } from 'lucide-react';
import { api } from '../api';
import { useLocale } from '../context/LocaleContext';

const createMessageId = (prefix) => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default function Chat() {
  const { isArabic } = useLocale();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [provider, setProvider] = useState('openai');
  const [copiedId, setCopiedId] = useState(null);
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  const t = useMemo(() => ({
    title: isArabic ? 'مساعد وزارة الاقتصاد الوطني' : 'Ministry Economy Assistant',
    subtitle: isArabic ? 'اختر الدائرة أولاً، ثم اسأل سؤالك للحصول على إجابة أدق.' : 'Choose a department first, then ask your question for better accuracy.',
    groupsTitle: isArabic ? 'مجموعات الدوائر' : 'Department Groups',
    noGroups: isArabic ? 'لا توجد مجموعات حالياً. أضف مجموعات من لوحة الإدارة.' : 'No groups yet. Add groups from Admin.',
    chooseGroup: isArabic ? 'اختر مجموعة' : 'Choose a group',
    docsCount: isArabic ? 'مستندات' : 'documents',
    selected: isArabic ? 'المجموعة المختارة' : 'Selected group',
    placeholder: isArabic ? 'اكتب سؤالك هنا...' : 'Type your question here...',
    thinking: isArabic ? 'جاري إعداد الإجابة' : 'Thinking',
    clear: isArabic ? 'مسح المحادثة' : 'Clear chat',
    stop: isArabic ? 'إيقاف' : 'Stop',
    regenerate: isArabic ? 'إعادة التوليد' : 'Regenerate',
    copy: isArabic ? 'نسخ' : 'Copy',
    enterToSend: isArabic ? 'اضغط Enter للإرسال' : 'Press Enter to send',
    groupHint: isArabic ? 'يمكنك تغيير المجموعة في أي وقت من البطاقات.' : 'You can switch group any time from cards.',
  }), [isArabic]);

  const colorClasses = {
    gold: 'from-[#f6e5ae] to-[#f2d676] border-[#cdab35] text-[#3f3520]',
    blue: 'from-[#e6f1ff] to-[#c9e0ff] border-[#4f85c6] text-[#24374f]',
    green: 'from-[#e5f8e9] to-[#caefcf] border-[#4ca769] text-[#1f4930]',
    red: 'from-[#ffeaea] to-[#ffd2d2] border-[#c96262] text-[#4a2525]',
    charcoal: 'from-[#e9edf0] to-[#d7dee4] border-[#6b7785] text-[#1f2933]',
  };

  const selectedGroup = groups.find((group) => group.id === selectedGroupId) || null;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    api.getConfig().then((c) => {
      if (c.active_provider) setProvider(c.active_provider);
    }).catch(() => {});

    api.getGroups().then((res) => {
      const loadedGroups = res?.groups || [];
      setGroups(loadedGroups);
      setSelectedGroupId((currentId) => {
        if (!loadedGroups.length) return '';
        if (currentId && loadedGroups.some((group) => group.id === currentId)) return currentId;
        return loadedGroups[0].id;
      });
    }).catch(() => {});
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  const handleSend = async (text) => {
    const message = (text || input).trim();
    if (!message || loading) return;

    const userId = createMessageId('user');
    const aiId = createMessageId('assistant');

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: message, id: userId }]);
    setLoading(true);
    setStreaming(true);
    setMessages((prev) => [...prev, { role: 'assistant', content: '', id: aiId }]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          provider,
          group_id: selectedGroupId || null,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        setMessages((prev) => prev.map((m) => (m.id === aiId ? { ...m, content: err.error || 'Request failed' } : m)));
        setLoading(false);
        setStreaming(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';
      let buffer = '';
      let shouldStop = false;
      abortRef.current = () => reader.cancel();

      while (!shouldStop) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') {
            shouldStop = true;
            break;
          }
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              fullContent += parsed.content;
              setMessages((prev) => prev.map((m) => (m.id === aiId ? { ...m, content: fullContent } : m)));
            } else if (parsed.error) {
              setMessages((prev) => prev.map((m) => (m.id === aiId ? { ...m, content: parsed.error } : m)));
              shouldStop = true;
              break;
            }
          } catch {
            // ignore malformed chunks
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMessages((prev) => prev.map((m) => (m.id === aiId ? { ...m, content: err.message } : m)));
      }
    } finally {
      setLoading(false);
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const clearChat = () => setMessages([]);

  const regenerate = () => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUserMsg) return;
    setMessages((prev) => prev.filter((m) => m.role !== 'assistant' || m.content));
    handleSend(lastUserMsg.content);
  };

  const copyMessage = (content, id) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const stopStreaming = () => {
    abortRef.current?.();
    setLoading(false);
    setStreaming(false);
  };

  const renderContent = (content) => {
    if (!content) return '';
    const escapeHtml = (value) => value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

    const inlineMarkdown = (value) => {
      let html = escapeHtml(value);
      html = html.replace(/`([^`]+)`/g, '<code class="bg-black/5 px-1.5 py-0.5 rounded text-sm font-mono text-[#5b4a17]">$1</code>');
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-[#15191d]">$1</strong>');
      return html;
    };

    const lines = content.split('\n');
    const parts = [];
    let listType = null;

    const closeList = () => {
      if (!listType) return;
      parts.push(listType === 'ol' ? '</ol>' : '</ul>');
      listType = null;
    };

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) {
        closeList();
        continue;
      }

      const orderedMatch = line.match(/^(\d+)\.\s+(.+)/);
      if (orderedMatch) {
        if (listType !== 'ol') {
          closeList();
          parts.push('<ol class="list-decimal list-inside space-y-1.5 my-3">');
          listType = 'ol';
        }
        parts.push(`<li>${inlineMarkdown(orderedMatch[2])}</li>`);
        continue;
      }

      const bulletMatch = line.match(/^[-*]\s+(.+)/);
      if (bulletMatch) {
        if (listType !== 'ul') {
          closeList();
          parts.push('<ul class="list-disc list-inside space-y-1.5 my-3">');
          listType = 'ul';
        }
        parts.push(`<li>${inlineMarkdown(bulletMatch[1])}</li>`);
        continue;
      }

      closeList();
      parts.push(`<p class="my-2">${inlineMarkdown(line)}</p>`);
    }

    closeList();
    return parts.join('');
  };

  return (
    <div className="flex flex-col h-full mne-soft-bg relative">
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-260px] left-[5%] w-[520px] h-[520px] rounded-full bg-[rgba(205,171,53,0.18)] blur-[120px]" />
        <div className="absolute bottom-[-280px] right-[3%] w-[560px] h-[560px] rounded-full bg-[rgba(35,40,45,0.13)] blur-[130px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto w-full px-4 pt-5">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`glass-card rounded-2xl p-4 mb-4 ${isArabic ? 'text-right' : 'text-left'}`}>
          <div className={`flex items-center gap-2 mb-1 ${isArabic ? 'flex-row-reverse justify-end' : ''}`}>
            <Layers size={16} className="text-[#8f7420]" />
            <div className="text-sm font-bold text-[#2b3138]">{t.groupsTitle}</div>
          </div>
          <p className="text-xs text-[#5b6672]">{t.groupHint}</p>

          {groups.length === 0 ? (
            <div className="text-sm text-[#7a8792] mt-3">{t.noGroups}</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
              {groups.map((group, index) => {
                const colorClass = colorClasses[group.color] || colorClasses.gold;
                const isSelected = group.id === selectedGroupId;
                return (
                  <motion.button
                    key={group.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04 }}
                    whileHover={{ y: -2, scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => setSelectedGroupId(group.id)}
                    className={`rounded-2xl border p-4 bg-gradient-to-br ${colorClass} text-left transition-all duration-300 ${
                      isSelected ? 'ring-2 ring-[#cdab35] shadow-xl shadow-[#cdab35]/25' : 'opacity-95 hover:opacity-100'
                    } ${isArabic ? 'text-right' : ''}`}
                  >
                    <div className={`flex items-center justify-between gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}>
                      <div className="font-bold text-sm break-words">{group.name}</div>
                      <FolderOpen size={16} className="flex-shrink-0" />
                    </div>
                    <div className="text-xs mt-2 opacity-85 min-h-[32px] line-clamp-2 break-words">{group.description || t.chooseGroup}</div>
                    <div className="text-[11px] mt-3 opacity-90">{(group.documents || []).length} {t.docsCount}</div>
                  </motion.button>
                );
              })}
            </div>
          )}

          {selectedGroup && (
            <div className={`mt-3 text-xs text-[#3e4852] ${isArabic ? 'text-right' : 'text-left'}`}>
              <span className="font-semibold">{t.selected}: </span>
              <span>{selectedGroup.name}</span>
            </div>
          )}
        </motion.div>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar relative z-10">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full px-4 py-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.55 }}
              className="text-center max-w-3xl"
            >
              <motion.img
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.45 }}
                src="/mne-logo.png"
                alt="MNE"
                className="w-56 sm:w-72 mx-auto mb-5"
              />
              <h1 className="text-3xl sm:text-4xl font-extrabold text-gradient mb-3">{t.title}</h1>
              <p className="text-[#4f5963] text-base sm:text-lg mb-3 max-w-2xl mx-auto">{t.subtitle}</p>
            </motion.div>
          </div>
        ) : (
          <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-4 ${msg.role === 'user' ? (isArabic ? 'justify-start' : 'justify-end') : (isArabic ? 'justify-end' : 'justify-start')}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-9 h-9 rounded-xl bg-[#23282d] text-white flex items-center justify-center shadow-lg">
                        <Bot size={18} />
                      </div>
                    </div>
                  )}

                  <div className="group max-w-[84%] sm:max-w-[75%]">
                    {msg.role === 'user' ? (
                      <div className={`glass-strong rounded-2xl px-5 py-3.5 ${isArabic ? 'rounded-tl-md text-right' : 'rounded-tr-md text-left'}`}>
                        <p className="text-sm leading-relaxed text-[#1b2025] whitespace-pre-wrap break-words">{msg.content}</p>
                      </div>
                    ) : (
                      <div className={`glass-card rounded-2xl px-5 py-4 ${isArabic ? 'rounded-tr-md text-right' : 'rounded-tl-md text-left'}`}>
                        {msg.content ? (
                          <div className="text-sm leading-7 text-[#263039] max-w-none whitespace-pre-wrap break-words" dangerouslySetInnerHTML={{ __html: renderContent(msg.content) }} />
                        ) : (
                          <div className={`flex items-center gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}>
                            <motion.div animate={{ opacity: [0.25, 1, 0.25] }} transition={{ duration: 1.3, repeat: Infinity }} className="flex gap-1">
                              <span className="w-2 h-2 rounded-full bg-[#cdab35]" />
                              <span className="w-2 h-2 rounded-full bg-[#cdab35]" />
                              <span className="w-2 h-2 rounded-full bg-[#cdab35]" />
                            </motion.div>
                            <span className="text-sm text-[#59626c]">{t.thinking}</span>
                          </div>
                        )}

                        <div className={`flex items-center gap-1.5 mt-3 opacity-0 group-hover:opacity-100 transition-opacity ${isArabic ? 'justify-start' : 'justify-end'}`}>
                          <button type="button" onClick={() => copyMessage(msg.content, msg.id)} className="p-1.5 rounded-lg hover:bg-black/5 text-[#676f78] hover:text-[#23282d] transition-all" title={t.copy}>
                            {copiedId === msg.id ? <Check size={14} /> : <Copy size={14} />}
                          </button>
                          {messages.length > 1 && (
                            <button type="button" onClick={regenerate} className="p-1.5 rounded-lg hover:bg-black/5 text-[#676f78] hover:text-[#23282d] transition-all" title={t.regenerate}>
                              <RefreshCw size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-9 h-9 rounded-xl bg-[#cdab35] text-white flex items-center justify-center shadow-lg shadow-[#cdab35]/35">
                        <User size={18} />
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="relative z-20 border-t border-black/10 bg-white/65 backdrop-blur-lg">
        <div className="max-w-5xl mx-auto px-4 py-4">
          {messages.length > 0 && (
            <div className="flex items-center justify-between mb-3">
              <button type="button" onClick={clearChat} className={`flex items-center gap-1.5 text-xs text-[#6b747d] hover:text-[#23282d] transition-colors ${isArabic ? 'flex-row-reverse' : ''}`}>
                <Trash2 size={14} />
                {t.clear}
              </button>
              {streaming && (
                <button type="button" onClick={stopStreaming} className={`flex items-center gap-1.5 text-xs text-red-600/75 hover:text-red-600 transition-colors ${isArabic ? 'flex-row-reverse' : ''}`}>
                  <StopCircle size={14} />
                  {t.stop}
                </button>
              )}
            </div>
          )}

          <div className="relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={t.placeholder}
              rows={1}
              className={`w-full input-premium ${isArabic ? 'pr-5 pl-14 text-right' : 'pl-5 pr-14 text-left'} resize-none`}
              style={{ maxHeight: 220 }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 220)}px`;
              }}
            />
            <div className={`absolute ${isArabic ? 'left-2' : 'right-2'} bottom-2 flex items-center gap-1`}>
              {(input.trim() || loading) && (
                <button
                  type="button"
                  onClick={() => (loading ? stopStreaming() : handleSend())}
                  disabled={!input.trim() && !loading}
                  className={`p-2.5 rounded-xl transition-all duration-300 ${loading ? 'bg-red-500/15 text-red-600 hover:bg-red-500/25' : 'btn-primary text-white'}`}
                >
                  {loading ? <StopCircle size={18} /> : <Send size={18} className={isArabic ? 'rotate-180' : ''} />}
                </button>
              )}
            </div>
          </div>

          <div className={`flex items-center mt-3 text-[11px] text-[#767f88] ${isArabic ? 'justify-start' : 'justify-end'}`}>
            <CornerDownLeft size={11} className={`inline ${isArabic ? 'ml-1' : 'mr-1'}`} />
            {t.enterToSend}
          </div>
        </div>
      </div>
    </div>
  );
}
