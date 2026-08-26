/**
 * Beyond Distance — Core Client Application Logic
 */

let state = {
    personas: [],
    activePersona: null,
    activeConversationId: null,
    conversations: [],
    memories: [],
    activeCategoryFilter: 'all',
    searchQuery: '',
    isSending: false,
    settings: {},
    allEvokedMap: {} // Map memory ID to memory object
};

// ================= INITIALIZATION =================
document.addEventListener('DOMContentLoaded', async () => {
    await loadSettings();
    await loadPersonas();
});

// ================= SETTINGS =================
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        state.settings = data.settings || {};
        
        // Update UI indicator
        const indicator = document.getElementById('providerIndicator');
        const label = document.getElementById('providerLabel');
        
        if (data.raw_keys_present?.gemini) {
            indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500/50';
            label.innerText = 'Gemini 2.5 Flash';
        } else if (data.raw_keys_present?.openai) {
            indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500/50';
            label.innerText = 'OpenAI GPT-4o';
        } else if (data.raw_keys_present?.groq) {
            indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-500/50';
            label.innerText = 'Groq Engine';
        } else {
            indicator.className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse';
            label.innerText = 'Offline Persona Engine';
        }
    } catch (e) {
        console.error('Failed to load settings', e);
    }
}

function openSettingsModal() {
    document.getElementById('settingsProvider').value = state.settings.llm_provider || 'auto';
    document.getElementById('settingsModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.add('hidden');
}

async function handleSaveSettings(e) {
    e.preventDefault();
    const provider = document.getElementById('settingsProvider').value;
    const geminiKey = document.getElementById('settingsGeminiKey').value;
    const openaiKey = document.getElementById('settingsOpenAIKey').value;
    const groqKey = document.getElementById('settingsGroqKey').value;

    const updates = [{ key: 'llm_provider', value: provider }];
    if (geminiKey) updates.push({ key: 'gemini_api_key', value: geminiKey });
    if (openaiKey) updates.push({ key: 'openai_api_key', value: openaiKey });
    if (groqKey) updates.push({ key: 'groq_api_key', value: groqKey });

    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ settings: updates })
        });
        closeSettingsModal();
        await loadSettings();
    } catch (e) {
        alert('Failed to save settings: ' + e.message);
    }
}

// ================= PERSONAS =================
async function loadPersonas() {
    try {
        const res = await fetch('/api/personas');
        state.personas = await res.json();
        
        if (state.personas.length > 0) {
            // Retain active or default to first
            const target = state.activePersona 
                ? state.personas.find(p => p.id === state.activePersona.id) || state.personas[0]
                : state.personas[0];
            selectPersona(target.id);
        }
        renderPersonaDropdown();
    } catch (e) {
        console.error('Failed to load personas', e);
    }
}

function renderPersonaDropdown() {
    const list = document.getElementById('personaDropdownList');
    list.innerHTML = '';
    
    state.personas.forEach(p => {
        const isCurrent = state.activePersona && state.activePersona.id === p.id;
        const item = document.createElement('div');
        item.className = `p-2 rounded-lg flex items-center justify-between cursor-pointer transition text-xs ${isCurrent ? 'bg-amber-500/20 text-amber-300 font-medium' : 'hover:bg-slate-800 text-slate-300'}`;
        item.innerHTML = `
            <div class="flex items-center gap-2.5 truncate">
                <span class="text-base">${p.avatar || '🌱'}</span>
                <div class="truncate">
                    <div class="font-medium truncate">${p.name}</div>
                    <div class="text-[10px] text-slate-400 truncate">${p.relationship}</div>
                </div>
            </div>
            <span class="text-[10px] text-slate-400">${p.memory_count || 0} mem</span>
        `;
        item.onclick = () => {
            selectPersona(p.id);
            togglePersonaDropdown(false);
        };
        list.appendChild(item);
    });
}

function togglePersonaDropdown(force) {
    const dropdown = document.getElementById('personaDropdown');
    if (force !== undefined) {
        dropdown.classList.toggle('hidden', !force);
    } else {
        dropdown.classList.toggle('hidden');
    }
}

async function selectPersona(personaId) {
    const persona = state.personas.find(p => p.id === personaId);
    if (!persona) return;
    
    state.activePersona = persona;

    // Update Sidebar
    document.getElementById('sidebarAvatar').innerText = persona.avatar || '🌱';
    document.getElementById('sidebarName').innerText = persona.name;
    document.getElementById('sidebarRelationship').innerText = persona.relationship;

    // Update Chat Header
    document.getElementById('chatHeaderAvatar').innerText = persona.avatar || '🌱';
    document.getElementById('chatHeaderName').innerText = persona.name;
    document.getElementById('chatHeaderRelBadge').innerText = persona.relationship;
    document.getElementById('chatHeaderTone').innerText = persona.tone_style || 'Warm & grounded';

    // Update Vault Title
    document.getElementById('vaultPersonaName').innerText = persona.name;

    // Update Studio form
    populateStudioForm(persona);

    // Refresh dependencies
    await loadMemories();
    await loadConversations();
    renderReflectionStarters(persona);
    renderPersonaDropdown();
}

// ================= CONVERSATIONS & CHAT =================
async function loadConversations() {
    if (!state.activePersona) return;
    try {
        const res = await fetch(`/api/personas/${state.activePersona.id}/conversations`);
        state.conversations = await res.json();
        
        const list = document.getElementById('conversationsList');
        list.innerHTML = '';

        if (state.conversations.length === 0) {
            // Auto create first conversation
            await createNewConversation();
            return;
        }

        state.conversations.forEach((c, idx) => {
            const isSelected = (!state.activeConversationId && idx === 0) || (state.activeConversationId === c.id);
            if (isSelected && !state.activeConversationId) {
                state.activeConversationId = c.id;
            }

            const item = document.createElement('div');
            item.className = `group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition ${isSelected ? 'bg-slate-800/90 text-amber-300 font-medium border border-slate-700/60 shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'}`;
            item.innerHTML = `
                <div class="flex items-center gap-2 truncate flex-1" onclick="selectConversation('${c.id}')">
                    <i data-lucide="message-square" class="w-3.5 h-3.5 shrink-0 opacity-60"></i>
                    <span class="truncate">${c.title || 'Conversation'}</span>
                </div>
                <button onclick="deleteConversation('${c.id}', event)" class="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 rounded transition" title="Delete">
                    <i data-lucide="trash" class="w-3 h-3"></i>
                </button>
            `;
            list.appendChild(item);
        });

        lucide.createIcons();

        if (state.activeConversationId) {
            await loadMessages(state.activeConversationId);
        }
    } catch (e) {
        console.error('Failed to load conversations', e);
    }
}

async function selectConversation(convId) {
    state.activeConversationId = convId;
    await loadConversations();
    await loadMessages(convId);
}

async function createNewConversation() {
    if (!state.activePersona) return;
    try {
        const res = await fetch(`/api/personas/${state.activePersona.id}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ persona_id: state.activePersona.id, title: 'New Conversation' })
        });
        const newConv = await res.json();
        state.activeConversationId = newConv.id;
        await loadConversations();
        await loadMessages(newConv.id);
    } catch (e) {
        console.error('Failed to create conversation', e);
    }
}

async function deleteConversation(convId, event) {
    if (event) event.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
        await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
        if (state.activeConversationId === convId) {
            state.activeConversationId = null;
        }
        await loadConversations();
    } catch (e) {
        console.error('Failed to delete conversation', e);
    }
}

async function clearCurrentConversation() {
    if (state.activeConversationId) {
        await deleteConversation(state.activeConversationId);
    }
}

async function loadMessages(convId) {
    const container = document.getElementById('chatMessagesContainer');
    container.innerHTML = '';

    try {
        const res = await fetch(`/api/conversations/${convId}`);
        const data = await res.json();
        
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                renderMessageBubble(msg);
            });
        } else {
            // Warm welcome placeholder
            renderWelcomePlaceholder();
        }
        scrollToBottom();
    } catch (e) {
        console.error('Failed to load messages', e);
    }
}

function renderWelcomePlaceholder() {
    const container = document.getElementById('chatMessagesContainer');
    const p = state.activePersona;
    if (!p) return;

    const el = document.createElement('div');
    el.className = 'flex flex-col items-center justify-center py-12 text-center text-slate-400 space-y-3 fade-in';
    el.innerHTML = `
        <div class="w-16 h-16 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-3xl shadow-lg">
            ${p.avatar || '🌱'}
        </div>
        <div class="max-w-md">
            <h3 class="font-heading font-semibold text-base text-slate-200">Reconnecting with ${p.name}</h3>
            <p class="text-xs text-slate-400 mt-1">${p.bio || 'Your personal connection space is open. Ask about a past memory, seek advice, or simply say hello.'}</p>
        </div>
    `;
    container.appendChild(el);
}

function renderMessageBubble(msg) {
    const container = document.getElementById('chatMessagesContainer');
    const isUser = msg.sender === 'user';
    const bubble = document.createElement('div');
    bubble.className = `flex gap-3 max-w-2xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'} fade-in`;

    let evokedHtml = '';
    if (!isUser && msg.evoked_memories && msg.evoked_memories.length > 0) {
        // Store in map for fast inspector access
        msg.evoked_memories.forEach(m => {
            state.allEvokedMap[m.id] = m;
        });

        const badges = msg.evoked_memories.map(m => `
            <button onclick="inspectMemory('${m.id}')" class="memory-badge text-[11px] px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow-sm">
                <i data-lucide="sparkles" class="w-3 h-3"></i>
                <span class="truncate max-w-[180px]">${m.title}</span>
            </button>
        `).join('');

        evokedHtml = `
            <div class="mt-3 pt-2.5 border-t border-slate-700/40 flex flex-wrap items-center gap-1.5">
                <span class="text-[10px] text-amber-400/90 font-medium uppercase tracking-wider">Evoked Memories:</span>
                ${badges}
            </div>
        `;
    }

    const formattedContent = msg.content
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>');

    bubble.innerHTML = `
        <div class="w-8 h-8 rounded-full ${isUser ? 'bg-blue-600' : 'bg-slate-800 border border-slate-700'} flex items-center justify-center text-sm shrink-0 select-none shadow-md">
            ${isUser ? '👤' : (state.activePersona?.avatar || '🌱')}
        </div>
        <div class="flex flex-col ${isUser ? 'items-end' : 'items-start'}">
            <div class="px-4 py-3 rounded-2xl text-xs leading-relaxed ${isUser ? 'message-user text-white rounded-tr-none' : 'message-persona text-slate-100 rounded-tl-none'}">
                <div>${formattedContent}</div>
                ${evokedHtml}
            </div>
            <span class="text-[10px] text-slate-500 mt-1 px-1">${formatTime(msg.created_at)}</span>
        </div>
    `;

    container.appendChild(bubble);
    lucide.createIcons();
}

function renderTypingIndicator() {
    const container = document.getElementById('chatMessagesContainer');
    const el = document.createElement('div');
    el.id = 'typingIndicator';
    el.className = 'flex gap-3 max-w-2xl mr-auto fade-in';
    el.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm shrink-0">
            ${state.activePersona?.avatar || '🌱'}
        </div>
        <div class="px-4 py-3 rounded-2xl message-persona rounded-tl-none flex items-center gap-1.5">
            <div class="w-2 h-2 rounded-full bg-amber-400 typing-dot"></div>
            <div class="w-2 h-2 rounded-full bg-amber-400 typing-dot"></div>
            <div class="w-2 h-2 rounded-full bg-amber-400 typing-dot"></div>
        </div>
    `;
    container.appendChild(el);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

async function handleSendMessage(e) {
    if (e) e.preventDefault();
    if (state.isSending || !state.activePersona) return;

    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    autoResizeTextarea(input);
    state.isSending = true;
    document.getElementById('sendBtn').disabled = true;

    // Remove welcome placeholder if present
    const welcome = document.querySelector('#chatMessagesContainer .flex-col.items-center');
    if (welcome) welcome.remove();

    // Optimistically render user message
    const tempUserMsg = {
        sender: 'user',
        content: text,
        created_at: new Date().toISOString()
    };
    renderMessageBubble(tempUserMsg);
    scrollToBottom();

    renderTypingIndicator();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: state.activeConversationId,
                persona_id: state.activePersona.id,
                message: text
            })
        });

        const data = await res.json();
        removeTypingIndicator();

        state.activeConversationId = data.conversation_id;

        // Render persona reply
        renderMessageBubble(data.persona_message);
        scrollToBottom();

        // Refresh conversation list titles if updated
        await loadConversations();
    } catch (err) {
        removeTypingIndicator();
        renderMessageBubble({
            sender: 'persona',
            content: "I'm having a little trouble connecting right now. Please try again in a moment.",
            created_at: new Date().toISOString()
        });
        console.error('Chat error:', err);
    } finally {
        state.isSending = false;
        document.getElementById('sendBtn').disabled = false;
    }
}

function handleTextareaKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function scrollToBottom() {
    const container = document.getElementById('chatMessagesContainer');
    container.scrollTop = container.scrollHeight;
}

function renderReflectionStarters(persona) {
    const startersBox = document.getElementById('starterButtons');
    startersBox.innerHTML = '';

    const defaultStarters = [
        `"What's one of your fondest memories of us?"`,
        `"I could really use some of your advice today."`,
        `"Do you remember that funny story we always laughed about?"`,
        `"Tell me about your favorite morning routine."`
    ];

    defaultStarters.forEach(promptText => {
        const btn = document.createElement('button');
        btn.className = 'px-3 py-1 rounded-full bg-slate-900/90 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 border border-slate-800 hover:border-amber-500/30 text-[11px] whitespace-nowrap transition';
        btn.innerText = promptText;
        btn.onclick = () => {
            document.getElementById('chatInput').value = promptText.replace(/^"|"$/g, '');
            handleSendMessage();
        };
        startersBox.appendChild(btn);
    });
}

// ================= MEMORY VAULT =================
async function loadMemories() {
    if (!state.activePersona) return;
    try {
        let url = `/api/personas/${state.activePersona.id}/memories`;
        const params = [];
        if (state.activeCategoryFilter && state.activeCategoryFilter !== 'all') {
            params.push(`category=${state.activeCategoryFilter}`);
        }
        if (state.searchQuery) {
            params.push(`search=${encodeURIComponent(state.searchQuery)}`);
        }
        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        const res = await fetch(url);
        state.memories = await res.json();
        
        // Update nav badge count
        document.getElementById('navMemoryCount').innerText = state.memories.length;

        renderMemoriesGrid();
    } catch (e) {
        console.error('Failed to load memories', e);
    }
}

function renderMemoriesGrid() {
    const grid = document.getElementById('memoriesGrid');
    const emptyState = document.getElementById('emptyMemoryState');
    grid.innerHTML = '';

    if (state.memories.length === 0) {
        emptyState.classList.remove('hidden');
        return;
    }
    emptyState.classList.add('hidden');

    state.memories.forEach(m => {
        const card = document.createElement('div');
        card.className = 'glass-card p-5 rounded-2xl flex flex-col justify-between space-y-3 fade-in group';

        const categoryClass = `cat-${m.category || 'story'}`;
        const categoryLabel = {
            story: 'Story',
            habit: 'Habit & Quirk',
            advice: 'Advice & Belief',
            chat_log: 'Chat Log / Letter',
            fact: 'Quick Fact'
        }[m.category] || 'Story';

        const stars = '★'.repeat(m.importance || 3) + '☆'.repeat(5 - (m.importance || 3));
        const tagsHtml = (m.tags || []).map(t => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-slate-800/80 text-slate-400">#${t}</span>`).join(' ');

        card.innerHTML = `
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-md ${categoryClass}">
                        ${categoryLabel}
                    </span>
                    <span class="text-amber-400 text-xs tracking-widest" title="Importance">${stars}</span>
                </div>
                <h4 class="font-heading font-semibold text-sm text-white group-hover:text-amber-300 transition">${m.title}</h4>
                <p class="text-xs text-slate-300 leading-relaxed line-clamp-4">${m.content}</p>
            </div>

            <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <div class="flex items-center gap-1.5 overflow-hidden">
                    ${m.date_reference ? `<span class="text-[10px] text-slate-400 flex items-center gap-1 truncate"><i data-lucide="calendar" class="w-3 h-3 text-slate-500"></i>${m.date_reference}</span>` : ''}
                </div>
                <div class="flex items-center gap-1">
                    <button onclick="openEditMemoryModal('${m.id}')" class="p-1.5 text-slate-400 hover:text-amber-400 rounded-lg hover:bg-slate-800 transition" title="Edit">
                        <i data-lucide="edit-2" class="w-3.5 h-3.5"></i>
                    </button>
                    <button onclick="deleteMemory('${m.id}')" class="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition" title="Delete">
                        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });

    lucide.createIcons();
}

function selectCategoryFilter(category) {
    state.activeCategoryFilter = category;
    document.querySelectorAll('.cat-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-cat') === category) {
            btn.className = 'cat-filter-btn px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30';
        } else {
            btn.className = 'cat-filter-btn px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800';
        }
    });
    loadMemories();
}

function filterMemories() {
    state.searchQuery = document.getElementById('memorySearchInput').value.trim();
    loadMemories();
}

// Memory Modal handlers
function openAddMemoryModal() {
    document.getElementById('memoryModalTitle').innerText = 'Add New Memory';
    document.getElementById('memoryId').value = '';
    document.getElementById('memTitle').value = '';
    document.getElementById('memCategory').value = 'story';
    document.getElementById('memDate').value = '';
    document.getElementById('memContent').value = '';
    document.getElementById('memTags').value = '';
    document.getElementById('memImportance').value = '3';
    document.getElementById('memoryModal').classList.remove('hidden');
    lucide.createIcons();
}

function openQuickMemoryModal() {
    openAddMemoryModal();
}

function openEditMemoryModal(memoryId) {
    const memory = state.memories.find(m => m.id === memoryId);
    if (!memory) return;

    document.getElementById('memoryModalTitle').innerText = 'Edit Memory';
    document.getElementById('memoryId').value = memory.id;
    document.getElementById('memTitle').value = memory.title;
    document.getElementById('memCategory').value = memory.category || 'story';
    document.getElementById('memDate').value = memory.date_reference || '';
    document.getElementById('memContent').value = memory.content;
    document.getElementById('memTags').value = (memory.tags || []).join(', ');
    document.getElementById('memImportance').value = String(memory.importance || 3);
    document.getElementById('memoryModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeMemoryModal() {
    document.getElementById('memoryModal').classList.add('hidden');
}

async function handleSaveMemory(e) {
    e.preventDefault();
    if (!state.activePersona) return;

    const memoryId = document.getElementById('memoryId').value;
    const title = document.getElementById('memTitle').value.trim();
    const category = document.getElementById('memCategory').value;
    const date_reference = document.getElementById('memDate').value.trim();
    const content = document.getElementById('memContent').value.trim();
    const tags = document.getElementById('memTags').value.split(',').map(t => t.trim()).filter(Boolean);
    const importance = parseInt(document.getElementById('memImportance').value);

    const payload = { title, category, date_reference, content, tags, importance };

    try {
        if (memoryId) {
            // Update
            await fetch(`/api/memories/${memoryId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // Create
            await fetch(`/api/personas/${state.activePersona.id}/memories`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        closeMemoryModal();
        await loadMemories();
        await loadPersonas(); // Update counts
    } catch (e) {
        alert('Failed to save memory: ' + e.message);
    }
}

async function deleteMemory(memoryId) {
    if (!confirm('Are you sure you want to remove this memory?')) return;
    try {
        await fetch(`/api/memories/${memoryId}`, { method: 'DELETE' });
        await loadMemories();
        await loadPersonas();
    } catch (e) {
        console.error('Failed to delete memory', e);
    }
}

// Bulk Import
function openBulkImportModal() {
    document.getElementById('bulkText').value = '';
    document.getElementById('bulkModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeBulkModal() {
    document.getElementById('bulkModal').classList.add('hidden');
}

async function handleBulkImport(e) {
    e.preventDefault();
    if (!state.activePersona) return;

    const text = document.getElementById('bulkText').value.trim();
    if (!text) return;

    try {
        await fetch(`/api/personas/${state.activePersona.id}/memories/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text: text })
        });
        closeBulkModal();
        await loadMemories();
        await loadPersonas();
    } catch (e) {
        alert('Failed to import memories: ' + e.message);
    }
}

// ================= MEMORY INSPECTOR DRAWER =================
function inspectMemory(memoryId) {
    const memory = state.allEvokedMap[memoryId] || state.memories.find(m => m.id === memoryId);
    if (!memory) return;

    const drawer = document.getElementById('memoryInspectorDrawer');
    const content = document.getElementById('inspectorContent');

    const categoryLabel = {
        story: 'Story / Experience',
        habit: 'Habit & Daily Quirk',
        advice: 'Advice & Belief',
        chat_log: 'Chat Log / Letter',
        fact: 'Quick Fact'
    }[memory.category] || 'Story';

    const tagsHtml = (memory.tags || []).map(t => `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-amber-300/80">#${t}</span>`).join(' ');

    content.innerHTML = `
        <div class="glass-panel p-4 rounded-xl space-y-2">
            <div class="flex items-center justify-between">
                <span class="text-[10px] uppercase font-bold text-amber-400 tracking-wider">${categoryLabel}</span>
                <span class="text-xs text-amber-300">Importance: ${'★'.repeat(memory.importance || 3)}</span>
            </div>
            <h4 class="font-heading font-bold text-base text-white">${memory.title}</h4>
            ${memory.date_reference ? `<div class="text-[11px] text-slate-400">📅 Timeframe: ${memory.date_reference}</div>` : ''}
        </div>

        <div class="space-y-2">
            <h5 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Preserved Memory Content</h5>
            <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
                ${memory.content}
            </div>
        </div>

        ${tagsHtml ? `
            <div class="space-y-2">
                <h5 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Associated Memory Tags</h5>
                <div class="flex flex-wrap gap-1.5">${tagsHtml}</div>
            </div>
        ` : ''}

        <div class="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300/90 leading-relaxed">
            ✦ This memory was retrieved and provided as ground truth context to embody the persona's authentic recollections during this conversation.
        </div>
    `;

    drawer.classList.remove('translate-x-full');
    lucide.createIcons();
}

function closeMemoryInspector() {
    document.getElementById('memoryInspectorDrawer').classList.add('translate-x-full');
}

// ================= PERSONA STUDIO =================
function populateStudioForm(persona) {
    document.getElementById('studioAvatar').value = persona.avatar || '🌱';
    document.getElementById('studioName').value = persona.name || '';
    document.getElementById('studioRelationship').value = persona.relationship || '';
    document.getElementById('studioBio').value = persona.bio || '';
    document.getElementById('studioTone').value = persona.tone_style || '';
    document.getElementById('studioCatchphrases').value = (persona.catchphrases || []).join('\n');
    
    document.getElementById('studioEmpathy').value = persona.empathy_level || 8;
    document.getElementById('empathyValue').innerText = (persona.empathy_level || 8) + '/10';
    
    document.getElementById('studioHumor').value = persona.humor_level || 5;
    document.getElementById('humorValue').innerText = (persona.humor_level || 5) + '/10';
    
    document.getElementById('studioNostalgia').value = persona.nostalgia_level || 7;
    document.getElementById('nostalgiaValue').innerText = (persona.nostalgia_level || 7) + '/10';
}

async function handleSavePersona(e) {
    e.preventDefault();
    if (!state.activePersona) return;

    const name = document.getElementById('studioName').value.trim();
    const avatar = document.getElementById('studioAvatar').value.trim() || '🌱';
    const relationship = document.getElementById('studioRelationship').value.trim();
    const bio = document.getElementById('studioBio').value.trim();
    const tone_style = document.getElementById('studioTone').value.trim();
    const catchphrases = document.getElementById('studioCatchphrases').value.split('\n').map(c => c.trim()).filter(Boolean);
    const empathy_level = parseInt(document.getElementById('studioEmpathy').value);
    const humor_level = parseInt(document.getElementById('studioHumor').value);
    const nostalgia_level = parseInt(document.getElementById('studioNostalgia').value);

    const payload = {
        name, avatar, relationship, bio, tone_style, catchphrases,
        empathy_level, humor_level, nostalgia_level
    };

    try {
        const res = await fetch(`/api/personas/${state.activePersona.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const updated = await res.json();
        await loadPersonas();
        selectPersona(updated.id);
        alert('Persona settings saved successfully!');
    } catch (err) {
        alert('Failed to save persona: ' + err.message);
    }
}

async function confirmDeletePersona() {
    if (!state.activePersona) return;
    if (!confirm(`Are you sure you want to delete "${state.activePersona.name}" and all associated memories? This cannot be undone.`)) return;

    try {
        await fetch(`/api/personas/${state.activePersona.id}`, { method: 'DELETE' });
        state.activePersona = null;
        state.activeConversationId = null;
        await loadPersonas();
        switchView('chat');
    } catch (e) {
        alert('Failed to delete persona: ' + e.message);
    }
}

// Create Persona Modal
function openCreatePersonaModal() {
    togglePersonaDropdown(false);
    document.getElementById('newPersonaAvatar').value = '🕊️';
    document.getElementById('newPersonaName').value = '';
    document.getElementById('newPersonaRelationship').value = '';
    document.getElementById('newPersonaTone').value = '';
    document.getElementById('createPersonaModal').classList.remove('hidden');
    lucide.createIcons();
}

function closeCreatePersonaModal() {
    document.getElementById('createPersonaModal').classList.add('hidden');
}

async function handleCreatePersona(e) {
    e.preventDefault();
    const avatar = document.getElementById('newPersonaAvatar').value.trim() || '🕊️';
    const name = document.getElementById('newPersonaName').value.trim();
    const relationship = document.getElementById('newPersonaRelationship').value.trim();
    const tone_style = document.getElementById('newPersonaTone').value.trim();

    try {
        const res = await fetch('/api/personas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, avatar, relationship, tone_style,
                catchphrases: [], empathy_level: 8, humor_level: 5, nostalgia_level: 7
            })
        });
        const newPersona = await res.json();
        closeCreatePersonaModal();
        await loadPersonas();
        selectPersona(newPersona.id);
        switchView('vault'); // take user to vault to add first memories
    } catch (err) {
        alert('Failed to create persona: ' + err.message);
    }
}

// ================= VIEW SWITCHING =================
function switchView(viewName) {
    document.getElementById('view-chat').classList.add('hidden');
    document.getElementById('view-vault').classList.add('hidden');
    document.getElementById('view-studio').classList.add('hidden');

    const navChat = document.getElementById('nav-chat');
    const navVault = document.getElementById('nav-vault');
    const navStudio = document.getElementById('nav-studio');

    const inactiveClass = 'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800/40';
    const activeClass = 'w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition text-amber-400 bg-amber-500/10 border border-amber-500/20';

    navChat.className = inactiveClass;
    navVault.className = inactiveClass;
    navStudio.className = inactiveClass;

    if (viewName === 'chat') {
        document.getElementById('view-chat').classList.remove('hidden');
        navChat.className = activeClass;
    } else if (viewName === 'vault') {
        document.getElementById('view-vault').classList.remove('hidden');
        navVault.className = activeClass;
        loadMemories();
    } else if (viewName === 'studio') {
        document.getElementById('view-studio').classList.remove('hidden');
        navStudio.className = activeClass;
    }

    lucide.createIcons();
}

// Helper formatting
function formatTime(isoString) {
    if (!isoString) return '';
    try {
        const d = new Date(isoString);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
}
