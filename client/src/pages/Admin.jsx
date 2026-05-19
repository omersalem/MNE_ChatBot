import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Server, Key, Activity, Database, RefreshCw, Trash2, Upload, Check, AlertTriangle, Eye, EyeOff,
  Settings2, Cpu, Wifi, WifiOff, Save, Bot, ChevronDown, ChevronUp, HardDrive, FileText,
  Layers, Plus, Pencil, X, FolderOpen,
} from 'lucide-react';
import { api, getAdminToken } from '../api';
import { useLocale } from '../context/LocaleContext';

function StatCard({ icon: Icon, label, value, color = 'blue' }) {
  const colors = {
    blue: 'from-blue-600/20 to-blue-600/5 border-blue-500/20 text-blue-400',
    cyan: 'from-cyan-600/20 to-cyan-600/5 border-cyan-500/20 text-cyan-400',
    violet: 'from-violet-600/20 to-violet-600/5 border-violet-500/20 text-violet-400',
    amber: 'from-amber-600/20 to-amber-600/5 border-amber-500/20 text-amber-400',
  };
  const c = colors[color] || colors.blue;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`glass-card rounded-2xl p-5 bg-gradient-to-br ${c}`}
    >
      <div className="flex items-center justify-between mb-3">
        <Icon size={20} className="opacity-70" />
      </div>
      <div className="text-2xl font-bold mb-0.5">{value}</div>
      <div className="text-xs font-medium opacity-60 tracking-wide">{label}</div>
    </motion.div>
  );
}

function Section({ title, icon: Icon, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-6 py-4 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Icon size={18} className="text-blue-400" />
          <h3 className="font-semibold text-sm text-white/80">{title}</h3>
        </div>
        {open ? <ChevronUp size={16} className="text-white/30" /> : <ChevronDown size={16} className="text-white/30" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/5"
          >
            <div className="px-6 py-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

const GROUP_COLOR_OPTIONS = [
  { value: 'gold', labelAr: 'ذهبي', labelEn: 'Gold', preview: 'from-[#f6e5ae] to-[#f2d676] border-[#cdab35]' },
  { value: 'blue', labelAr: 'أزرق', labelEn: 'Blue', preview: 'from-[#e6f1ff] to-[#c9e0ff] border-[#4f85c6]' },
  { value: 'green', labelAr: 'أخضر', labelEn: 'Green', preview: 'from-[#e5f8e9] to-[#caefcf] border-[#4ca769]' },
  { value: 'red', labelAr: 'أحمر', labelEn: 'Red', preview: 'from-[#ffeaea] to-[#ffd2d2] border-[#c96262]' },
  { value: 'charcoal', labelAr: 'فحمي', labelEn: 'Charcoal', preview: 'from-[#e9edf0] to-[#d7dee4] border-[#6b7785]' },
];

export default function Admin() {
  const { isArabic } = useLocale();
  const [config, setConfig] = useState(null);
  const [stats, setStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState({});
  const [apiKeys, setApiKeys] = useState({});
  const [keyInputs, setKeyInputs] = useState({});
  const [visibleKeys, setVisibleKeys] = useState({});
  const [savingKey, setSavingKey] = useState({});
  const [uploading, setUploading] = useState(false);
  const [groups, setGroups] = useState([]);
  const [groupDocuments, setGroupDocuments] = useState([]);
  const [editingGroupId, setEditingGroupId] = useState('');
  const [groupSaving, setGroupSaving] = useState(false);
  const [groupForm, setGroupForm] = useState({ name: '', description: '', color: 'gold', documents: [] });
  const [toast, setToast] = useState(null);
  const fileInputRef = useRef(null);

  const t = useMemo(() => ({
    adminDashboard: isArabic ? 'لوحة الإدارة' : 'Admin Dashboard',
    adminDesc: isArabic ? 'إدارة منصة المساعد الذكي للوزارة' : 'Manage the ministry assistant platform',
    refresh: isArabic ? 'تحديث' : 'Refresh',
    totalChunks: isArabic ? 'إجمالي المقاطع' : 'Total Chunks',
    documents: isArabic ? 'الوثائق' : 'Documents',
    activeProvider: isArabic ? 'المزوّد النشط' : 'Active Provider',
    model: isArabic ? 'النموذج' : 'Model',
    providerModelConfig: isArabic ? 'إعدادات المزوّد والنموذج' : 'Provider & Model Configuration',
    activeProviderLabel: isArabic ? 'المزوّد النشط' : 'Active Provider',
    activeModelLabel: isArabic ? 'النموذج النشط' : 'Active Model',
    modelsCount: isArabic ? 'نماذج' : 'models',
    apiKeyManagement: isArabic ? 'إدارة مفاتيح API' : 'API Key Management',
    configured: isArabic ? 'مُعدّ' : 'Configured',
    notSet: isArabic ? 'غير مُعدّ' : 'Not Set',
    enterNewApiKey: isArabic ? 'أدخل مفتاح API جديد' : 'Enter new API key',
    enterApiKey: isArabic ? 'أدخل مفتاح API لـ' : 'Enter',
    saveKey: isArabic ? 'حفظ المفتاح' : 'Save Key',
    providerStatus: isArabic ? 'حالة المزوّدات' : 'Provider Status',
    noProviderHealth: isArabic ? 'لا توجد بيانات حالة بعد. أضف مفاتيح API لعرض الحالة.' : 'No provider health data yet. Add API keys to view status.',
    documentManagement: isArabic ? 'إدارة الوثائق' : 'Document Management',
    uploadingIndexing: isArabic ? 'جاري الرفع والفهرسة...' : 'Uploading and indexing...',
    dropOrClick: isArabic ? 'اسحب الملف هنا أو اضغط للرفع' : 'Drop a file here or click to upload',
    uploadTypes: isArabic ? 'PDF, DOCX, TXT, MD - حتى 50MB' : 'PDF, DOCX, TXT, MD - up to 50MB',
    reindexAll: isArabic ? 'إعادة فهرسة الكل' : 'Reindex All',
    documentsIndexed: isArabic ? 'وثيقة مفهرسة' : 'documents indexed',
    filename: isArabic ? 'اسم الملف' : 'Filename',
    type: isArabic ? 'النوع' : 'Type',
    chunks: isArabic ? 'المقاطع' : 'Chunks',
    actions: isArabic ? 'الإجراءات' : 'Actions',
    reindex: isArabic ? 'إعادة فهرسة' : 'Reindex',
    delete: isArabic ? 'حذف' : 'Delete',
    noDocuments: isArabic ? 'لا توجد وثائق مفهرسة بعد' : 'No documents indexed yet',
    noDocumentsHint: isArabic ? 'يمكنك رفع ملفات جديدة أو وضعها داخل مجلد company_docs' : 'Upload new files or place them in company_docs',
    switchedProvider: isArabic ? 'تم تبديل المزوّد إلى' : 'Provider switched to',
    modelSet: isArabic ? 'تم تعيين النموذج إلى' : 'Model set to',
    keySaved: isArabic ? 'تم حفظ مفتاح API لـ' : 'API key saved for',
    reindexing: isArabic ? 'جاري إعادة فهرسة جميع الوثائق...' : 'Reindexing all documents...',
    reindexComplete: isArabic ? 'اكتملت إعادة الفهرسة' : 'Reindex complete',
    indexed: isArabic ? 'تمت فهرسة' : 'Indexed',
    uploadFailed: isArabic ? 'فشل الرفع' : 'Upload failed',
    reindexed: isArabic ? 'تمت إعادة فهرسة' : 'Reindexed',
    deleted: isArabic ? 'تم حذف' : 'Deleted',
    connected: isArabic ? 'متصل' : 'connected',
    failed: isArabic ? 'فشل' : 'failed',
    noKey: isArabic ? 'لا يوجد مفتاح' : 'no_key',
    uninitialized: isArabic ? 'غير مهيأ' : 'uninitialized',
    groupManagement: isArabic ? 'إدارة مجموعات الدوائر' : 'Department Group Management',
    groupDesc: isArabic ? 'أنشئ مجموعات للدائرة واربط كل مجموعة بوثائقها لتوجيه الإجابات بدقة.' : 'Create department groups and attach documents for focused answers.',
    groupName: isArabic ? 'اسم المجموعة' : 'Group Name',
    groupDescription: isArabic ? 'وصف المجموعة' : 'Group Description',
    groupColor: isArabic ? 'لون المجموعة' : 'Group Color',
    groupDocumentsLabel: isArabic ? 'وثائق المجموعة' : 'Group Documents',
    newGroup: isArabic ? 'مجموعة جديدة' : 'New Group',
    saveGroup: isArabic ? 'حفظ المجموعة' : 'Save Group',
    updateGroup: isArabic ? 'تحديث المجموعة' : 'Update Group',
    cancelEdit: isArabic ? 'إلغاء التعديل' : 'Cancel Edit',
    noGroupDocs: isArabic ? 'لا توجد وثائق متاحة حالياً. ارفع وثائق أولاً.' : 'No documents available yet. Upload documents first.',
    groupsList: isArabic ? 'المجموعات الحالية' : 'Current Groups',
    noGroups: isArabic ? 'لا توجد مجموعات بعد. ابدأ بإنشاء أول مجموعة.' : 'No groups yet. Create your first group.',
    groupSaved: isArabic ? 'تم حفظ المجموعة' : 'Group saved',
    groupUpdated: isArabic ? 'تم تحديث المجموعة' : 'Group updated',
    groupDeleted: isArabic ? 'تم حذف المجموعة' : 'Group deleted',
    groupNameRequired: isArabic ? 'اسم المجموعة مطلوب' : 'Group name is required',
    confirmDeleteGroup: isArabic ? 'هل تريد حذف هذه المجموعة؟' : 'Delete this group?',
  }), [isArabic]);

  const statusLabel = (status) => {
    if (status === 'connected') return t.connected;
    if (status === 'failed') return t.failed;
    if (status === 'no_key') return t.noKey;
    if (status === 'uninitialized') return t.uninitialized;
    return status || '-';
  };

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchAll = async () => {
    try {
      const [cfg, st, docs, h, keys, groupsRes, groupDocsRes] = await Promise.all([
        api.getConfig().catch(() => null),
        api.getStats().catch(() => null),
        api.getDocuments().catch(() => []),
        api.getHealth().catch(() => ({})),
        api.getApiKeys().catch(() => ({ keys: {} })),
        api.getGroupsAdmin().catch(() => ({ groups: [] })),
        api.getGroupDocuments().catch(() => ({ documents: [] })),
      ]);
      setConfig(cfg);
      setStats(st);
      setDocuments(docs?.documents || docs || []);
      setHealth(h?.providers || h || {});
      setApiKeys(keys?.keys || {});
      setGroups(groupsRes?.groups || []);
      setGroupDocuments(groupDocsRes?.documents || []);
    } catch {
      // no-op
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSetProvider = async (provider) => {
    try {
      await api.setProvider(provider);
      showToast(`${t.switchedProvider} ${provider}`);
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleSetModel = async (model) => {
    try {
      await api.setModel(model);
      showToast(`${t.modelSet} ${model}`);
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleSaveKey = async (provider) => {
    const key = keyInputs[provider]?.trim();
    if (!key) return;
    setSavingKey((prev) => ({ ...prev, [provider]: true }));
    try {
      await api.saveApiKey(provider, key);
      showToast(`${t.keySaved} ${provider}`);
      setKeyInputs((prev) => ({ ...prev, [provider]: '' }));
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSavingKey((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const handleReindexAll = async () => {
    try {
      showToast(t.reindexing);
      await api.reindexAll();
      showToast(t.reindexComplete);
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setUploading(true);
    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        headers: { 'X-Admin-Token': getAdminToken() },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        showToast(`${t.indexed} ${data.filename} (${data.chunks})`);
        fetchAll();
      } else {
        showToast(data.error || t.uploadFailed, 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    handleUpload(file);
  };

  const handleDragOver = (e) => e.preventDefault();

  const providerColors = {
    openai: { bg: 'from-green-600/20 to-green-600/5 border-green-500/20', dot: 'bg-green-400' },
    anthropic: { bg: 'from-amber-600/20 to-amber-600/5 border-amber-500/20', dot: 'bg-amber-400' },
    openrouter: { bg: 'from-blue-600/20 to-blue-600/5 border-blue-500/20', dot: 'bg-blue-400' },
    gemini: { bg: 'from-cyan-600/20 to-cyan-600/5 border-cyan-500/20', dot: 'bg-cyan-400' },
    ollama: { bg: 'from-violet-600/20 to-violet-600/5 border-violet-500/20', dot: 'bg-violet-400' },
    litellm: { bg: 'from-rose-600/20 to-rose-600/5 border-rose-500/20', dot: 'bg-rose-400' },
    glm5: { bg: 'from-indigo-600/20 to-indigo-600/5 border-indigo-500/20', dot: 'bg-indigo-400' },
  };

  const resetGroupForm = () => {
    setEditingGroupId('');
    setGroupForm({ name: '', description: '', color: 'gold', documents: [] });
  };

  const startEditGroup = (group) => {
    setEditingGroupId(group.id);
    setGroupForm({
      name: group.name || '',
      description: group.description || '',
      color: group.color || 'gold',
      documents: Array.isArray(group.documents) ? group.documents : [],
    });
  };

  const toggleGroupDocument = (docName) => {
    setGroupForm((prev) => {
      const exists = prev.documents.includes(docName);
      return {
        ...prev,
        documents: exists ? prev.documents.filter((name) => name !== docName) : [...prev.documents, docName],
      };
    });
  };

  const handleSaveGroup = async () => {
    if (!groupForm.name.trim()) {
      showToast(t.groupNameRequired, 'error');
      return;
    }
    setGroupSaving(true);
    try {
      const payload = {
        name: groupForm.name.trim(),
        description: groupForm.description.trim(),
        color: groupForm.color,
        documents: groupForm.documents,
      };
      if (editingGroupId) {
        await api.updateGroup(editingGroupId, payload);
        showToast(t.groupUpdated);
      } else {
        await api.createGroup(payload);
        showToast(t.groupSaved);
      }
      resetGroupForm();
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setGroupSaving(false);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (!window.confirm(t.confirmDeleteGroup)) return;
    try {
      await api.deleteGroup(groupId);
      if (editingGroupId === groupId) resetGroupForm();
      showToast(t.groupDeleted);
      fetchAll();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  return (
    <div className={`admin-theme h-full overflow-y-auto no-scrollbar relative ${isArabic ? 'text-right' : 'text-left'}`} dir={isArabic ? 'rtl' : 'ltr'}>
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-200px] right-[-200px] w-[500px] h-[500px] bg-violet-600/5 rounded-full blur-[100px]" />
        <div className="absolute bottom-[-200px] left-[-200px] w-[400px] h-[400px] bg-blue-600/5 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-6 space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-2xl font-bold">
              <span className="text-gradient-violet">{t.adminDashboard}</span>
            </h1>
            <p className="text-sm text-white/40 mt-1">{t.adminDesc}</p>
          </div>
          <button onClick={fetchAll} className={`btn-ghost flex items-center gap-2 text-sm ${isArabic ? 'flex-row-reverse' : ''}`}>
            <RefreshCw size={14} />
            {t.refresh}
          </button>
        </motion.div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Database} label={t.totalChunks} value={stats?.total_chunks || 0} color="blue" />
          <StatCard icon={FileText} label={t.documents} value={stats?.unique_documents || 0} color="cyan" />
          <StatCard icon={Server} label={t.activeProvider} value={config?.active_provider || '-'} color="violet" />
          <StatCard icon={Cpu} label={t.model} value={config?.active_model?.split('-').slice(0, 2).join(' ') || '-'} color="amber" />
        </div>

        <Section title={t.providerModelConfig} icon={Settings2}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <label className="text-xs font-medium text-white/40 uppercase tracking-wider">{t.activeProviderLabel}</label>
              <div className="grid grid-cols-2 gap-2">
                {config?.providers && Object.entries(config.providers).map(([name, info]) => {
                  const pc = providerColors[name] || providerColors.openai;
                  const isActive = config.active_provider === name;
                  return (
                    <motion.button
                      key={name}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleSetProvider(name)}
                      className={`relative rounded-xl p-3.5 border transition-all duration-300 bg-gradient-to-br ${pc.bg} ${isActive ? 'ring-2 ring-blue-500/30 shadow-glow' : 'opacity-60 hover:opacity-80'} ${isArabic ? 'text-right' : 'text-left'}`}
                    >
                      <div className={`flex items-center gap-2.5 ${isArabic ? 'flex-row-reverse' : ''}`}>
                        <div className={`w-2 h-2 rounded-full ${pc.dot} ${isActive ? 'animate-pulse' : ''}`} />
                        <span className="text-sm font-medium capitalize">{name}</span>
                        {isActive && <Check size={14} className={isArabic ? 'mr-auto text-blue-400' : 'ml-auto text-blue-400'} />}
                      </div>
                      {info.models && <span className="text-xs text-white/30 mt-1.5 block">{info.models.length} {t.modelsCount}</span>}
                    </motion.button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-3">
              <label className="text-xs font-medium text-white/40 uppercase tracking-wider">{t.activeModelLabel}</label>
              <div className="space-y-2">
                {config?.providers?.[config.active_provider]?.models?.map((model) => (
                  <motion.button
                    key={model}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleSetModel(model)}
                    className={`w-full rounded-xl px-4 py-3 border transition-all duration-300 flex items-center gap-3 ${config.active_model === model ? 'bg-blue-600/15 border-blue-500/30 shadow-glow' : 'bg-white/[0.02] border-white/5 hover:border-white/10 text-white/50 hover:text-white/70'} ${isArabic ? 'text-right flex-row-reverse' : 'text-left'}`}
                  >
                    <Bot size={16} className={config.active_model === model ? 'text-blue-400' : 'text-white/20'} />
                    <span className="text-sm font-medium">{model}</span>
                    {config.active_model === model && <Check size={14} className={isArabic ? 'mr-auto text-blue-400' : 'ml-auto text-blue-400'} />}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        </Section>

        <Section title={t.apiKeyManagement} icon={Key}>
          <div className="space-y-4">
            {config?.providers && Object.keys(config.providers).map((provider) => (
              <motion.div
                key={provider}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass rounded-xl p-4 hover:bg-white/[0.03] transition-colors"
              >
                <div className={`flex flex-col sm:flex-row items-start sm:items-center gap-3 ${isArabic ? 'sm:flex-row-reverse' : ''}`}>
                  <div className="flex-1 w-full">
                    <div className={`flex items-center gap-2 mb-2 ${isArabic ? 'flex-row-reverse justify-end' : ''}`}>
                      <span className="text-sm font-medium capitalize text-white/70">{provider}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${apiKeys[provider]?.configured ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                        {apiKeys[provider]?.configured ? t.configured : t.notSet}
                      </span>
                    </div>
                    <div className="relative">
                      <input
                        type={visibleKeys[provider] ? 'text' : 'password'}
                        value={keyInputs[provider] || ''}
                        onChange={(e) => setKeyInputs((prev) => ({ ...prev, [provider]: e.target.value }))}
                        placeholder={apiKeys[provider]?.configured ? apiKeys[provider]?.key_preview || t.enterNewApiKey : `${t.enterApiKey} ${provider} API key`}
                        className={`w-full input-premium text-sm ${isArabic ? 'pl-20 text-right' : 'pr-20 text-left'}`}
                      />
                      <div className={`absolute top-1/2 -translate-y-1/2 flex items-center gap-1 ${isArabic ? 'left-2' : 'right-2'}`}>
                        <button
                          onClick={() => setVisibleKeys((prev) => ({ ...prev, [provider]: !prev[provider] }))}
                          className="p-1.5 rounded-lg hover:bg-white/5 text-white/30 hover:text-white/60 transition-colors"
                        >
                          {visibleKeys[provider] ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                      </div>
                    </div>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleSaveKey(provider)}
                    disabled={savingKey[provider] || !keyInputs[provider]?.trim()}
                    className={`btn-primary flex items-center gap-2 text-sm whitespace-nowrap disabled:opacity-50 ${isArabic ? 'flex-row-reverse' : ''}`}
                  >
                    {savingKey[provider] ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : (<><Save size={14} />{t.saveKey}</>)}
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </div>
        </Section>

        <Section title={t.providerStatus} icon={Activity}>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {Object.entries(health).map(([name, status]) => (
              <div key={name} className="glass rounded-xl p-4 flex items-center justify-between">
                <div className={`flex items-center gap-3 ${isArabic ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-2.5 h-2.5 rounded-full ${status?.status === 'connected' ? 'bg-green-400 animate-pulse' : status?.status === 'failed' ? 'bg-red-400' : 'bg-amber-400'}`} />
                  <div>
                    <span className="text-sm font-medium capitalize text-white/70">{name}</span>
                    <span className="block text-xs text-white/30">{statusLabel(status?.status)}</span>
                  </div>
                </div>
                {status?.status === 'connected' ? <Wifi size={14} className="text-green-400" /> : <WifiOff size={14} className="text-red-400" />}
              </div>
            ))}
            {Object.keys(health).length === 0 && (
              <div className="col-span-full text-center text-sm text-white/30 py-8">{t.noProviderHealth}</div>
            )}
          </div>
        </Section>

        <Section title={t.groupManagement} icon={Layers}>
          <div className="space-y-5">
            <div className="text-xs text-white/45">{t.groupDesc}</div>

            <div className="glass rounded-2xl p-4 space-y-4">
              <div className={`flex items-center justify-between gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}>
                <div className="text-sm font-semibold text-white/80">{editingGroupId ? t.updateGroup : t.newGroup}</div>
                {editingGroupId ? (
                  <button type="button" onClick={resetGroupForm} className={`btn-ghost text-xs flex items-center gap-1.5 ${isArabic ? 'flex-row-reverse' : ''}`}>
                    <X size={13} />
                    {t.cancelEdit}
                  </button>
                ) : null}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-white/45 block mb-1.5">{t.groupName}</label>
                  <input
                    value={groupForm.name}
                    onChange={(e) => setGroupForm((prev) => ({ ...prev, name: e.target.value }))}
                    className={`input-premium text-sm ${isArabic ? 'text-right' : 'text-left'}`}
                  />
                </div>
                <div>
                  <label className="text-xs text-white/45 block mb-1.5">{t.groupColor}</label>
                  <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
                    {GROUP_COLOR_OPTIONS.map((option) => (
                      <button
                        type="button"
                        key={option.value}
                        onClick={() => setGroupForm((prev) => ({ ...prev, color: option.value }))}
                        className={`rounded-xl border px-2 py-2 text-[11px] font-semibold text-[#25313c] bg-gradient-to-br ${option.preview} ${groupForm.color === option.value ? 'ring-2 ring-[#cdab35]' : 'opacity-90 hover:opacity-100'} ${isArabic ? 'text-right' : 'text-left'}`}
                      >
                        {isArabic ? option.labelAr : option.labelEn}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <label className="text-xs text-white/45 block mb-1.5">{t.groupDescription}</label>
                <textarea
                  rows={2}
                  value={groupForm.description}
                  onChange={(e) => setGroupForm((prev) => ({ ...prev, description: e.target.value }))}
                  className={`input-premium text-sm resize-none ${isArabic ? 'text-right' : 'text-left'}`}
                />
              </div>

              <div>
                <label className="text-xs text-white/45 block mb-2">{t.groupDocumentsLabel}</label>
                {groupDocuments.length === 0 ? (
                  <div className="text-xs text-white/35">{t.noGroupDocs}</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-44 overflow-y-auto pr-1">
                    {groupDocuments.map((docName) => {
                      const selected = groupForm.documents.includes(docName);
                      return (
                        <button
                          type="button"
                          key={docName}
                          onClick={() => toggleGroupDocument(docName)}
                          className={`w-full rounded-xl border px-3 py-2 text-xs transition-all duration-200 ${selected ? 'bg-blue-600/20 border-blue-500/35 text-blue-200' : 'bg-white/[0.02] border-white/10 text-white/70 hover:border-white/25'} ${isArabic ? 'text-right' : 'text-left'}`}
                        >
                          <div className={`flex items-center gap-2 ${isArabic ? 'flex-row-reverse justify-end' : ''}`}>
                            <div className={`w-4 h-4 rounded-md border flex items-center justify-center ${selected ? 'border-blue-300 bg-blue-500/30' : 'border-white/25'}`}>
                              {selected ? <Check size={11} /> : null}
                            </div>
                            <span className="truncate">{docName}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className={`flex items-center gap-2 ${isArabic ? 'flex-row-reverse justify-start' : ''}`}>
                <button
                  type="button"
                  onClick={handleSaveGroup}
                  disabled={groupSaving}
                  className={`btn-primary text-sm flex items-center gap-2 disabled:opacity-60 ${isArabic ? 'flex-row-reverse' : ''}`}
                >
                  {groupSaving ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={14} />}
                  {editingGroupId ? t.updateGroup : t.saveGroup}
                </button>
                <button type="button" onClick={resetGroupForm} className={`btn-ghost text-sm flex items-center gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}>
                  <Plus size={14} />
                  {t.newGroup}
                </button>
              </div>
            </div>

            <div>
              <div className="text-sm font-semibold text-white/80 mb-3">{t.groupsList}</div>
              {groups.length === 0 ? (
                <div className="text-sm text-white/35">{t.noGroups}</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {groups.map((group, index) => {
                    const color = GROUP_COLOR_OPTIONS.find((item) => item.value === group.color) || GROUP_COLOR_OPTIONS[0];
                    return (
                      <motion.div
                        key={group.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.04 }}
                        className={`rounded-2xl border p-4 bg-gradient-to-br ${color.preview}`}
                      >
                        <div className={`flex items-start justify-between gap-2 ${isArabic ? 'flex-row-reverse' : ''}`}>
                          <div className={`${isArabic ? 'text-right' : 'text-left'}`}>
                            <div className="font-bold text-[#1f2933]">{group.name}</div>
                            <div className="text-xs text-[#41505f] mt-1">{group.description || '-'}</div>
                          </div>
                          <FolderOpen size={17} className="text-[#2f3a46]" />
                        </div>
                        <div className="mt-3 text-xs text-[#2d3844]">
                          {(group.documents || []).length} {isArabic ? 'مستند' : 'documents'}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {(group.documents || []).slice(0, 4).map((doc) => (
                            <span key={`${group.id}-${doc}`} className="px-2 py-0.5 rounded-full text-[10px] bg-white/60 text-[#2b3138]">
                              {doc}
                            </span>
                          ))}
                          {(group.documents || []).length > 4 ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] bg-white/60 text-[#2b3138]">
                              +{(group.documents || []).length - 4}
                            </span>
                          ) : null}
                        </div>
                        <div className={`mt-3 flex items-center gap-2 ${isArabic ? 'flex-row-reverse justify-start' : ''}`}>
                          <button
                            type="button"
                            onClick={() => startEditGroup(group)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border border-[#33414d]/35 bg-white/70 text-[#27323d] hover:bg-white/90 transition-all flex items-center gap-1.5 ${isArabic ? 'flex-row-reverse' : ''}`}
                          >
                            <Pencil size={12} />
                            {isArabic ? 'تعديل' : 'Edit'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteGroup(group.id)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border border-red-700/30 bg-white/70 text-red-700 hover:bg-red-50 transition-all flex items-center gap-1.5 ${isArabic ? 'flex-row-reverse' : ''}`}
                          >
                            <Trash2 size={12} />
                            {t.delete}
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </Section>

        <Section title={t.documentManagement} icon={HardDrive}>
          <div className="space-y-4">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              className="glass rounded-xl p-6 border-2 border-dashed border-white/10 hover:border-blue-500/30 transition-all duration-300 cursor-pointer text-center group"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md"
                className="hidden"
                onChange={(e) => handleUpload(e.target.files[0])}
              />
              {uploading ? (
                <div className={`flex items-center justify-center gap-3 ${isArabic ? 'flex-row-reverse' : ''}`}>
                  <div className="w-6 h-6 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                  <span className="text-sm text-white/50">{t.uploadingIndexing}</span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload size={24} className="text-white/20 group-hover:text-blue-400 transition-colors" />
                  <span className="text-sm text-white/40 group-hover:text-white/60 transition-colors">{t.dropOrClick}</span>
                  <span className="text-xs text-white/20">{t.uploadTypes}</span>
                </div>
              )}
            </div>

            <div className={`flex items-center gap-3 ${isArabic ? 'flex-row-reverse' : ''}`}>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleReindexAll}
                className={`btn-primary flex items-center gap-2 text-sm ${isArabic ? 'flex-row-reverse' : ''}`}
              >
                <RefreshCw size={14} />
                {t.reindexAll}
              </motion.button>
              <span className="text-xs text-white/30">{documents.length} {t.documentsIndexed}</span>
            </div>

            {documents.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className={`border-b border-white/5 ${isArabic ? 'text-right' : 'text-left'}`}>
                      <th className="pb-3 font-medium text-white/40 text-xs uppercase tracking-wider">{t.filename}</th>
                      <th className="pb-3 font-medium text-white/40 text-xs uppercase tracking-wider">{t.type}</th>
                      <th className="pb-3 font-medium text-white/40 text-xs uppercase tracking-wider">{t.chunks}</th>
                      <th className="pb-3 font-medium text-white/40 text-xs uppercase tracking-wider">{t.actions}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc, i) => (
                      <motion.tr
                        key={doc.filename}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors"
                      >
                        <td className="py-3 font-medium text-white/70">
                          <div className={`flex items-center gap-2 ${isArabic ? 'flex-row-reverse justify-end' : ''}`}>
                            <FileText size={14} className="text-blue-400/50" />
                            {doc.filename}
                          </div>
                        </td>
                        <td className="py-3 text-white/40">{doc.document_type}</td>
                        <td className="py-3">
                          <span className="px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-300/80 text-xs">{doc.chunk_count}</span>
                        </td>
                        <td className="py-3">
                          <div className={`flex items-center gap-2 ${isArabic ? 'flex-row-reverse justify-end' : ''}`}>
                            <button
                              onClick={async () => {
                                try {
                                  await api.reindexDocument(doc.filename);
                                  showToast(`${t.reindexed} ${doc.filename}`);
                                  fetchAll();
                                } catch (err) {
                                  showToast(err.message, 'error');
                                }
                              }}
                              className="p-1.5 rounded-lg hover:bg-blue-500/10 text-blue-400/60 hover:text-blue-400 transition-colors"
                              title={t.reindex}
                            >
                              <RefreshCw size={14} />
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  await api.deleteDocument(doc.filename);
                                  showToast(`${t.deleted} ${doc.filename}`);
                                  fetchAll();
                                } catch (err) {
                                  showToast(err.message, 'error');
                                }
                              }}
                              className="p-1.5 rounded-lg hover:bg-red-500/10 text-red-400/60 hover:text-red-400 transition-colors"
                              title={t.delete}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText size={32} className="mx-auto text-white/10 mb-3" />
                <p className="text-sm text-white/30">{t.noDocuments}</p>
                <p className="text-xs text-white/20 mt-1">{t.noDocumentsHint}</p>
              </div>
            )}
          </div>
        </Section>
      </div>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className={`fixed bottom-6 ${isArabic ? 'left-6' : 'right-6'} z-50 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-sm font-medium ${toast.type === 'error' ? 'bg-red-500/20 border border-red-500/30 text-red-300' : 'bg-green-500/20 border border-green-500/30 text-green-300'} ${isArabic ? 'flex-row-reverse' : ''}`}
          >
            {toast.type === 'error' ? <AlertTriangle size={16} /> : <Check size={16} />}
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
