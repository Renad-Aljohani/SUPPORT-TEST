// مصدر واحد لحالة النموذج حتى تتشارك واجهتا الموظف والدعم نفس الطلبات.
const STORAGE_KEY = 'iu-support-prototype-v2';

window.addEventListener('storage', event => {
  if (event.key === STORAGE_KEY) location.reload();
});

const seedState = {
  tickets: [
    {
      id: 'REQ-1048', title: 'تعذر الاتصال بالشبكة اللاسلكية', type: 'مشكلة تقنية', department: 'الموارد البشرية',
      priority: 'عالية', status: 'جديد', createdAt: '24 أغسطس، 09:42 ص', requester: 'لينا محمد', assignee: '',
      responseTime: 'بانتظار الاستلام', description: 'يتعذر الاتصال بشبكة المكتب من جهاز العمل، وتظهر رسالة تفيد بعدم إمكانية الاتصال بالشبكة رغم إعادة تشغيل الجهاز',
      attachment: { name: 'رسالة-الخطأ.png', size: '842 KB' }, solution: '', solutionAt: '', rating: null,
      timeline: [{ title: 'أُنشئ الطلب', meta: 'لينا محمد — 24 أغسطس، 09:42 ص' }]
    },
    {
      id: 'REQ-1046', title: 'تهيئة الطابعة المكتبية', type: 'صيانة', department: 'المشتريات',
      priority: 'متوسطة', status: 'قيد المعالجة', createdAt: '24 أغسطس، 08:35 ص', requester: 'عمر راشد', assignee: 'ريناد الجهني',
      responseTime: 'متبقي 1 س 12 د', description: 'الطابعة الجديدة متصلة بالشبكة، لكنها لا تظهر ضمن أجهزة الطباعة المتاحة على جهاز العمل',
      attachment: null, solution: '', solutionAt: '', rating: null,
      timeline: [
        { title: 'أُنشئ الطلب', meta: 'عمر راشد — 24 أغسطس، 08:35 ص' },
        { title: 'استلمت ريناد الجهني الطلب', meta: '24 أغسطس، 08:41 ص' }
      ]
    },
    {
      id: 'REQ-1042', title: 'طلب تثبيت برنامج Power BI', type: 'طلب خدمة', department: 'المالية',
      priority: 'متوسطة', status: 'بانتظار تأكيد الموظف', createdAt: '23 أغسطس، 01:50 م', requester: 'لينا محمد', assignee: 'أحمد الزحيلي',
      responseTime: 'بانتظار تأكيد الحل', description: 'أحتاج إلى تثبيت برنامج Power BI على جهاز العمل لاستخدامه في إعداد التقارير المالية',
      attachment: null, solution: 'تم تثبيت البرنامج وتسجيل الدخول بالحساب المؤسسي، ثم اختبار فتح التقارير بنجاح', solutionAt: '23 أغسطس، 03:15 م', rating: null,
      messages: [
        { sender: 'employee', name: 'لينا محمد', text: 'أحتاج إلى تثبيت Power BI على جهاز العمل', time: '01:50 م' },
        { sender: 'support', name: 'أحمد الزحيلي', text: 'ما الموعد المناسب للدخول على الجهاز وتثبيت البرنامج؟', time: '02:15 م' }
      ],
      timeline: [
        { title: 'أُنشئ الطلب', meta: 'لينا محمد — 23 أغسطس، 01:50 م' },
        { title: 'استلم أحمد الزحيلي الطلب', meta: '23 أغسطس، 02:04 م' },
        { title: 'أُرسل الحل للتأكيد', meta: 'أحمد الزحيلي — 23 أغسطس، 03:15 م' }
      ]
    },
    {
      id: 'REQ-1037', title: 'بطء في جهاز العمل', type: 'صيانة', department: 'التشغيل',
      priority: 'منخفضة', status: 'مغلق', createdAt: '21 أغسطس، 08:15 ص', requester: 'لينا محمد', assignee: 'عبدالرحيم عبيد',
      responseTime: 'أُغلق خلال 3 س', description: 'أصبح جهاز العمل بطيئاً عند تشغيل البرامج وفتح الملفات، ويستغرق وقتاً طويلاً للاستجابة رغم إعادة تشغيله',
      attachment: { name: 'مواصفات-الجهاز.png', size: '524 KB' }, solution: 'تم تنظيف الملفات المؤقتة وتحديث تعريفات الجهاز وإعادة تشغيله، ثم التأكد من عودة الأداء إلى وضعه الطبيعي', solutionAt: '21 أغسطس، 11:20 ص', rating: null,
      timeline: [
        { title: 'أُنشئ الطلب', meta: 'لينا محمد — 21 أغسطس، 08:15 ص' },
        { title: 'استلم عبدالرحيم عبيد الطلب', meta: '21 أغسطس، 08:28 ص' },
        { title: 'أُرسل الحل للتأكيد', meta: 'عبدالرحيم عبيد — 21 أغسطس، 11:20 ص' },
        { title: 'أكدت لينا محمد الحل وأُغلق الطلب', meta: '21 أغسطس، 11:30 ص' }
      ]
    },
    {
      id: 'REQ-1029', title: 'إعادة تعيين كلمة مرور البريد', type: 'استفسار / استشارة', department: 'المشتريات',
      priority: 'عالية', status: 'مغلق', createdAt: '19 أغسطس، 07:48 ص', requester: 'عمر راشد', assignee: 'ريناد الجهني',
      responseTime: 'أُغلق خلال 18 د', description: 'تعذر تسجيل الدخول إلى البريد الإلكتروني بعد نسيان كلمة المرور، وأحتاج إلى إعادة تعيينها',
      attachment: null, solution: 'تمت إعادة تعيين كلمة المرور والتحقق من نجاح تسجيل الدخول إلى البريد الإلكتروني', solutionAt: '19 أغسطس، 08:02 ص', rating: { value: 5, comment: 'استجابة سريعة وحل واضح' },
      timeline: [
        { title: 'أُنشئ الطلب', meta: 'عمر راشد — 19 أغسطس، 07:48 ص' },
        { title: 'استلمت ريناد الجهني الطلب', meta: '19 أغسطس، 07:52 ص' },
        { title: 'أُرسل الحل للتأكيد', meta: 'ريناد الجهني — 19 أغسطس، 08:02 ص' },
        { title: 'أكد عمر راشد الحل وأُغلق الطلب', meta: '19 أغسطس، 08:06 ص' }
      ]
    }
  ],
  drafts: [],
  notifications: {
    employee: [
      { id: 'e1', ticketId: 'REQ-1042', title: 'الحل جاهز للتأكيد', text: 'راجع الحل المرسل لطلب تثبيت Power BI', time: 'منذ 20 دقيقة', read: false },
      { id: 'e2', ticketId: 'REQ-1037', title: 'قيّم خدمة الدعم الفني', text: 'أكمل تقييم الطلب بعد تأكيد الحل', time: 'اليوم، 11:32 ص', read: false }
    ],
    support: [
      { id: 's1', ticketId: 'REQ-1048', title: 'طلب دعم جديد', text: 'تعذر الاتصال بالشبكة اللاسلكية', time: 'منذ 5 دقائق', read: false },
      { id: 's2', ticketId: 'REQ-1029', title: 'تقييم جديد للخدمة', text: 'تم تقييم الطلب بخمس نجوم', time: 'منذ 25 دقيقة', read: true }
    ]
  }
};

const paths = {
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  tickets: '<path d="M4 5h16v14H4z"/><path d="M8 9h8M8 13h5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  headset: '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><path d="M18 19h-2v-7h4v5a2 2 0 0 1-2 2ZM6 19h2v-7H4v5a2 2 0 0 0 2 2Z"/><path d="M16 19c0 2-2 3-4 3"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c.6-5 3.2-7 8-7s7.4 2 8 7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  file: '<path d="M6 2h8l4 4v16H6z"/><path d="M14 2v5h5"/>',
  arrow: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
  inbox: '<path d="M4 4h16v16H4z"/><path d="m4 14 5-1 2 3h2l2-3 5 1"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  star: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.3L5.8 21 7 14.2 2 9.3l6.9-1z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  paperclip: '<path d="m21 11.5-8.8 8.8a6 6 0 0 1-8.5-8.5L13 2.5a4 4 0 0 1 5.7 5.7L9.4 17.5a2 2 0 1 1-2.8-2.8l8.6-8.6"/>'
};

export function icon(name, label = '') {
  const aria = label ? `role="img" aria-label="${escapeHTML(label)}"` : 'aria-hidden="true"';
  return `<span class="icon" ${aria}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.file}</svg></span>`;
}

export function loadState() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const state = stored ? JSON.parse(stored) : structuredClone(seedState);
    state.tickets.forEach(ticket => {
      if (!Array.isArray(ticket.messages)) ticket.messages = [];
      if (ticket.id === 'REQ-1037' && ticket.messages.length === 0) {
        ticket.messages = [
          { sender: 'employee', name: 'لينا محمد', text: 'الجهاز ما زال بطيئاً عند فتح الملفات والبرامج', time: '08:18 ص' },
          { sender: 'support', name: 'عبدالرحيم عبيد', text: 'تم استلام الطلب، وسأفحص التعريفات والملفات المؤقتة', time: '08:30 ص' }
        ];
      }
    });
    return state;
  } catch {
    return structuredClone(seedState);
  }
}

export function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function escapeHTML(value = '') {
  return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
}

export function getTicket(state, id) {
  return state.tickets.find(ticket => ticket.id === id);
}

export function readRoute(defaultRoute) {
  const [route, ticketId = null] = location.hash.replace(/^#/, '').split('/');
  return { route: route || defaultRoute, ticketId };
}

export function nowArabic() {
  return new Intl.DateTimeFormat('ar-SA', { day: 'numeric', month: 'long', hour: 'numeric', minute: '2-digit' }).format(new Date());
}

export function statusBadge(status) {
  const classes = {
    'جديد': 'status-new',
    'قيد المعالجة': 'status-processing',
    'بانتظار تأكيد الموظف': 'status-confirmation',
    'بانتظار التقييم': 'status-confirmation',
    'مغلق': 'status-closed',
    'مسودة': 'status-draft'
  };
  return `<span class="status ${classes[status] || 'status-new'}">${escapeHTML(status)}</span>`;
}

export function priorityBadge(priority) {
  const classes = { 'عالية': 'priority-high', 'متوسطة': 'priority-medium', 'منخفضة': 'priority-low' };
  return `<span class="priority ${classes[priority] || 'priority-medium'}">${escapeHTML(priority)}</span>`;
}


const ticketStages = [
  { key: 'new', label: 'جديد' },
  { key: 'processing', label: 'قيد المعالجة' },
  { key: 'confirmation', label: 'بانتظار التأكيد' },
  { key: 'closed', label: 'مغلق' }
];

function ticketStageIndex(status) {
  const indexes = {
    'جديد': 0,
    'قيد المعالجة': 1,
    'بانتظار تأكيد الموظف': 2,
    'بانتظار التقييم': 3,
    'مغلق': 3
  };
  return indexes[status] ?? 0;
}

export function renderTicketHero(ticket) {
  return `<section class="detail-hero">
    <div class="detail-kicker"><strong>تفاصيل الطلب</strong><span class="ticket-code">${escapeHTML(ticket.id)}</span></div>
    <h1>${escapeHTML(ticket.title)}</h1>
    <div class="detail-meta">
      <span>${escapeHTML(ticket.type)}</span>
      <span>${escapeHTML(ticket.department)}</span>
      <span>${icon('clock')} أُنشئ ${escapeHTML(ticket.createdAt)}</span>
    </div>
  </section>`;
}

export function renderTicketProgress(ticket) {
  const activeIndex = ticketStageIndex(ticket.status);
  return `<nav class="ticket-progress" aria-label="مراحل الطلب">
    ${ticketStages.map((stage, index) => {
      const stateClass = index < activeIndex ? 'is-complete' : index === activeIndex ? 'is-current' : '';
      const marker = index < activeIndex ? icon('check') : `<span>${index + 1}</span>`;
      return `<div class="ticket-stage ${stateClass}" ${index === activeIndex ? 'aria-current="step"' : ''}>
        <span class="ticket-stage-marker">${marker}</span>
        <span class="ticket-stage-label">${stage.label}</span>
      </div>`;
    }).join('')}
  </nav>`;
}

export function statCard(iconName, number, label, featured = false, tone = 'total') {
  return `<article class="stat-card ${featured ? 'featured' : ''}" data-tone="${escapeHTML(tone)}"><span class="stat-icon">${icon(iconName)}</span><div><strong>${number}</strong><span>${label}</span></div></article>`;
}

export function renderAttachment(ticket) {
  if (!ticket.attachment) return '';
  return `<div class="attachment"><span class="file-icon">${icon('paperclip')}</span><span><strong>${escapeHTML(ticket.attachment.name)}</strong><small>${escapeHTML(ticket.attachment.size)}</small></span></div>`;
}

export function renderChat(ticket, currentRole, canSend = true) {
  const messages = ticket.messages || [];
  return `<section class="surface chat-card">
    <div class="surface-header"><h2>المحادثة داخل الطلب</h2></div>
    <div class="chat-body" id="chat-body">
      ${messages.length ? messages.map(message => `<article class="chat-message ${message.sender === currentRole ? 'mine' : 'theirs'}"><strong>${escapeHTML(message.name)}</strong><p>${escapeHTML(message.text)}</p><small>${escapeHTML(message.time)}</small></article>`).join('') : '<div class="chat-empty">لا توجد رسائل حتى الآن</div>'}
    </div>
    ${canSend ? `<div class="chat-composer">
      <button class="chat-attach" type="button" id="chat-attach" aria-label="إرفاق ملف">${icon('paperclip')}<span class="button-label">إرفاق</span></button>
      <input class="chat-input" id="chat-input" type="text" placeholder="اكتب رسالتك..." aria-label="نص الرسالة">
      <button class="button chat-send" type="button" id="chat-send">${icon('send')}<span class="button-label">إرسال</span></button>
      <input id="chat-file" type="file" hidden>
    </div>` : ''}
  </section>`;
}

export function bindChat({ ticket, role, name, onChange }) {
  const input = document.getElementById('chat-input');
  const send = document.getElementById('chat-send');
  const file = document.getElementById('chat-file');
  if (!input || !send) return;
  const submit = () => {
    const text = input.value.trim();
    if (!text) return;
    ticket.messages.push({ sender: role, name, text, time: new Intl.DateTimeFormat('ar-SA', { hour: 'numeric', minute: '2-digit' }).format(new Date()) });
    onChange();
  };
  send.addEventListener('click', submit);
  input.addEventListener('keydown', event => { if (event.key === 'Enter') submit(); });
  document.getElementById('chat-attach')?.addEventListener('click', () => file.click());
  file?.addEventListener('change', () => {
    if (!file.files[0]) return;
    ticket.messages.push({ sender: role, name, text: `مرفق: ${file.files[0].name}`, time: new Intl.DateTimeFormat('ar-SA', { hour: 'numeric', minute: '2-digit' }).format(new Date()) });
    onChange();
  });
}

export function renderTimeline(items) {
  return `<ol class="timeline">${items.map(item => `<li><strong>${escapeHTML(item.title)}</strong><small>${escapeHTML(item.meta)}</small></li>`).join('')}</ol>`;
}

export function addNotification(state, role, ticketId, title, text) {
  state.notifications[role].unshift({ id: `${role}-${Date.now()}`, ticketId, title, text, time: 'الآن', read: false });
}

export function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 2600);
}

export function mountShell({ role, active, navigate }) {
  const isEmployee = role === 'employee';
  const homePage = isEmployee ? '/support/employee' : '/support/manager';
  const items = isEmployee
    ? [{ key: 'requests', label: 'الرئيسية' }, { key: 'new', label: 'إنشاء طلب' }]
    : [{ key: 'dashboard', label: 'الرئيسية' }, { key: 'performance', label: 'سجل الإنجاز' }];
  const topbar = document.getElementById('topbar');
 topbar.className = 'topbar';
topbar.innerHTML = `
  <div class="topbar-inner">
<div aria-hidden="true"></div>

      <nav class="main-nav" aria-label="التنقل الرئيسي">
        ${items.map(item => `<a href="#${item.key}" class="nav-link ${active === item.key ? 'active' : ''}" data-route="${item.key}"><span>${item.label}</span></a>`).join('')}
      </nav>
      <div class="nav-actions">
        <button class="icon-button" id="notifications-button" type="button" aria-label="الإشعارات" aria-expanded="false">
          ${icon('bell')}<span class="notification-count" id="notification-count">0</span>
        </button>
        <section class="notifications-panel" id="notifications-panel" aria-label="الإشعارات" hidden></section>
      </div>
    </div>`;

  topbar.querySelectorAll('[data-route]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    navigate(link.dataset.route);
  }));
}

export function bindNotifications(state, role, openTicket) {
  const button = document.getElementById('notifications-button');
  const panel = document.getElementById('notifications-panel');
  const count = document.getElementById('notification-count');

  const draw = () => {
    const items = state.notifications[role] || [];
    const unread = items.filter(item => !item.read).length;
    count.textContent = unread;
    count.hidden = unread === 0;
    panel.innerHTML = `<div class="panel-head"><strong>الإشعارات</strong><button class="text-button" id="mark-read" type="button">تحديد الكل كمقروء</button></div>
      <div class="notification-list">${items.length ? items.map(item => `
        <button type="button" class="notification-item ${item.read ? '' : 'unread'}" data-notification="${item.id}">
          <span class="notification-icon">${icon('bell')}</span>
          <span><strong>${escapeHTML(item.title)}</strong><p>${escapeHTML(item.text)}</p><small>${escapeHTML(item.time)}</small></span>
        </button>`).join('') : '<div class="empty-state">لا توجد إشعارات</div>'}</div>`;
    panel.querySelector('#mark-read')?.addEventListener('click', () => {
      items.forEach(item => { item.read = true; });
      saveState(state);
      draw();
    });
    panel.querySelectorAll('[data-notification]').forEach(itemButton => itemButton.addEventListener('click', () => {
      const item = items.find(entry => entry.id === itemButton.dataset.notification);
      if (!item) return;
      item.read = true;
      saveState(state);
      panel.hidden = true;
      openTicket(item.ticketId);
    }));
  };

  draw();
  button.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    button.setAttribute('aria-expanded', String(!panel.hidden));
  });
  if (!document.body.dataset.notificationsOutsideBound) {
    document.body.dataset.notificationsOutsideBound = 'true';
    document.addEventListener('click', event => {
      if (!event.target.closest('.nav-actions')) {
        const currentPanel = document.getElementById('notifications-panel');
        if (currentPanel) currentPanel.hidden = true;
      }
    });
  }
}
