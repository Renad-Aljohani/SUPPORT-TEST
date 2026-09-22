/** @odoo-module **/

import { registry } from "@web/core/registry";

const app =   document.getElementById('app');
const CURRENT_SUPPORT_ID = Number(app?.dataset.supportId);


const isManagerPage =
  app?.dataset.supportName !== undefined;

/*
 * هوية الهيدر.
 * مسار الشعار افتراضيًا داخل موديل website. ولو نُقلت الملفات إلى موديل
 * آخر، يكفي تمرير المسار من القالب عبر data-brand-logo على عنصر #app
 * دون تعديل هذا الملف. وإن فُقد الملف يخفيه الحارس أسفل هذا القسم،
 * فيظهر اسم المنصة نصًا دون صورة مكسورة.
 */
const BRAND_NAME =
  app?.dataset.brandName ||
  'معهد البحوث والدراسات الاستشارية';

const BRAND_LOGO =
  app?.dataset.brandLogo ||
  '/website/static/src/img/logo-mark-color.png';

const PORTAL_NAME =
  app?.dataset.portalName ||
  'منصة الدعم الفني';

const paths = {
  /* طقم واحد لكل الواجهة: شبكة ٢٤، حجم بصري ~١٧، نهايات مستديرة،
     ونفس وزن الخط في كل أيقونة. الواجهتان تستعملان الطقم نفسه. */
  tickets: '<path d="M5 4.6h14a1 1 0 0 1 1 1v12.8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5.6a1 1 0 0 1 1-1Z"/><path d="M8 9.4h8"/><path d="M8 13.4h5"/>',

  inbox: '<path d="M6.7 5.6h10.6L20 13.4v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-4Z"/><path d="M20 13.4h-4.2l-1.5 2.4h-4.6l-1.5-2.4H4"/>',

  clock: '<circle cx="12" cy="12" r="8.2"/><path d="M12 7.4V12l3.1 1.9"/>',

  check: '<path d="m5.6 12.4 4.2 4.2 8.6-8.6"/>',

  bell: '<path d="M18 9.1a6 6 0 1 0-12 0c0 5.2-2 6.3-2 7.7h16c0-1.4-2-2.5-2-7.7Z"/><path d="M10.2 19.8a2.2 2.2 0 0 0 3.6 0"/>',

  send: '<path d="M20.4 3.6 10.9 13.1"/><path d="M20.4 3.6 14.2 20.4l-3.3-7.3-7.3-3.3Z"/>',

  star: '<path d="m12 4.2 2.5 5.1 5.6.8-4.1 4 .9 5.6-5-2.6-5 2.6.9-5.6-4-4 5.6-.8Z"/>',

  paperclip: '<path d="m19.4 11.7-7.1 7.1a4.4 4.4 0 0 1-6.3-6.3l7.6-7.6a3 3 0 0 1 4.2 4.2l-7.6 7.6a1.5 1.5 0 0 1-2.1-2.1l6.9-6.9"/>',

  search: '<circle cx="11" cy="11" r="6.6"/><path d="m15.8 15.8 4.2 4.2"/>',

  user: '<circle cx="12" cy="8.4" r="3.8"/><path d="M4.9 20.2c.9-3.9 3.4-5.8 7.1-5.8s6.2 1.9 7.1 5.8"/>',

  arrow: '<path d="M19.4 12H4.6"/><path d="m10.6 18-6-6 6-6"/>',

  plus: '<path d="M12 5.4v13.2"/><path d="M5.4 12h13.2"/>',

  dashboard: '<rect x="4" y="4" width="7" height="7" rx="1.4"/><rect x="13" y="4" width="7" height="7" rx="1.4"/><rect x="4" y="13" width="7" height="7" rx="1.4"/><rect x="13" y="13" width="7" height="7" rx="1.4"/>',

  headset: '<path d="M4.6 14.2v-2a7.4 7.4 0 0 1 14.8 0v2"/><path d="M17.6 19.4h-1.4v-6.2h3.2v4.2a2 2 0 0 1-1.8 2ZM6.4 19.4h1.4v-6.2H4.6v4.2a2 2 0 0 0 1.8 2Z"/><path d="M16.2 19.4c0 1.6-1.7 2.6-3.6 2.6"/>',

  chart: '<path d="M4.6 19.4V10.6"/><path d="M9.5 19.4V4.6"/><path d="M14.5 19.4v-6.6"/><path d="M19.4 19.4V8.4"/>',

  file: '<path d="M13.6 4.2H7.4A1.4 1.4 0 0 0 6 5.6v12.8a1.4 1.4 0 0 0 1.4 1.4h9.2a1.4 1.4 0 0 0 1.4-1.4V8.6Z"/><path d="M13.6 4.2v4.4H18"/>'
};



let supportBus = null;

const supportChatBusService = {
  dependencies: ['bus_service'],

  start(env, { bus_service }) {
    if (!isManagerPage) {
    return;
  }
    supportBus = bus_service;

    bus_service.addEventListener(
      'notification',
      async ({ detail: notifications }) => {
        for (const notification of notifications) {
          const {
            type,
            payload
          } = notification;

          if (
            type !==
            'support_chat_message'
          ) {
            continue;
          }

          if (
            currentRoute === 'detail' &&
            selectedTicketId ===
              payload.ticket_number
          ) {
            const ticket =
              getTicket(
                state,
                selectedTicketId
              );

            if (ticket) {
              await renderDetail(
                ticket.id
              );
            }
          }
        }
      }
    );
  },
};

registry.category(
  'services'
).add(
  'manager_support_chat_bus_service',
  supportChatBusService
);

function escapeHTML(value = '') {
  return String(value).replace(
    /[&<>'"]/g,
    char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    })[char]
  );
}
function formatDateTime(value) {
  if (!value) {
    return '';
  }

  return new Intl.DateTimeFormat(
    'ar-SA-u-ca-gregory-nu-latn',
    {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }
  ).format(
    new Date(value)
  );
}
function icon(name, label = '') {
  const aria = label
    ? `role="img" aria-label="${escapeHTML(label)}"`
    : 'aria-hidden="true"';

  return `
    <span class="icon" ${aria}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.9"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        ${paths[name] || paths.file}
      </svg>
    </span>
  `;
}

function getTicket(stateObject, id) {
  return stateObject.tickets.find(
    ticket => ticket.id === id
  );
}

function readRoute(defaultRoute) {
  const [route, ticketId = null] =
    location.hash
      .replace(/^#/, '')
      .split('/');

  return {
    route: route || defaultRoute,
    ticketId
  };
}

function statusBadge(status) {
  const classes = {
    'جديد': 'status-new',
    'قيد المعالجة': 'status-processing',
    'معلق مؤقتًا':'status-on-hold',
    'بانتظار تأكيد الموظف': 'status-confirmation',
    'بانتظار التقييم': 'status-confirmation',
    'مغلق': 'status-closed',
    'مسودة': 'status-draft'
  };

  return `
    <span class="status ${classes[status] || 'status-new'}">
      ${escapeHTML(status)}
    </span>
  `;
}

function priorityBadge(priority) {
  const classes = {
    'عالية': 'priority-high',
    'متوسطة': 'priority-medium',
    'منخفضة': 'priority-low'
  };

  return `
    <span class="priority ${classes[priority] || 'priority-medium'}">
      ${escapeHTML(priority)}
    </span>
  `;
}

const ticketStages = [
  { label: 'جديد' },
  { label: 'قيد المعالجة' },
  { label: 'بانتظار تأكيد الموظف' },
  { label: 'مغلق' }
];

function ticketStageIndex(status) {
  const indexes = {
    'جديد': 0,
    'قيد المعالجة': 1,
        'معلق مؤقتًا': 1,
    'بانتظار تأكيد الموظف': 2,
    'بانتظار التقييم': 3,
    'مغلق': 3
  };

  return indexes[status] ?? 0;
}

function renderSlaBadge(ticket) {

  const percent =
    Number(
      ticket.sla_resolution_percent || 0
    );

  const hours =
    Number(
      ticket.sla_resolution_remaining_hours || 0
    );

  const status =
    ticket.sla_resolution_status;

  const paused =
    ticket.status === 'معلق مؤقتًا';


  let tone =
    'sla-badge-safe';

  let text = '';


  if (paused) {

    tone =
      'sla-badge-paused';

    text =
      'SLA متوقف مؤقتًا';

  } else if (
    status === 'successful'
  ) {

    tone =
      'sla-badge-success';

    text =
      'SLA محقق';

  } else if (
    status === 'failed'
    || percent >= 100
  ) {

    tone =
      'sla-badge-danger';

    text =
      'SLA متجاوز';

  } else if (
    percent >= 90
  ) {

    tone =
      'sla-badge-danger';

    text =
      `متبقي ${
        formatSlaHours(
          hours
        )
      }`;

  } else if (
    percent >= 75
  ) {

    tone =
      'sla-badge-warning';

    text =
      `متبقي ${
        formatSlaHours(
          hours
        )
      }`;

  } else {

    tone =
      'sla-badge-safe';

    text =
      `متبقي ${
        formatSlaHours(
          hours
        )
      }`;

  }


  return `
    <span
      class="
        sla-badge
        ${tone}
      "
    >
      ${escapeHTML(text)}
    </span>
  `;
}


function formatSlaHours(hours) {

  if (
    !hours
    || hours <= 0
  ) {
    return '0 س';
  }

  const wholeHours =
    Math.floor(hours);

  const minutes =
    Math.round(
      (
        hours - wholeHours
      ) * 60
    );

  if (
    wholeHours > 0
    && minutes > 0
  ) {

    return (
      `${wholeHours} س `
      + `${minutes} د`
    );

  }

  if (wholeHours > 0) {
    return `${wholeHours} س`;
  }

  return `${minutes} د`;
}

function renderTicketHero(ticket, facts = []) {
  return `
    <section class="detail-hero">

    <div class="detail-kicker">

  <span class="kicker-main">

    <strong>
      تفاصيل الطلب
    </strong>

    <span class="ticket-code">
      ${escapeHTML(ticket.id)}
    </span>

  </span>

  <div class="detail-status-group">

  ${statusBadge(ticket.status)}

  ${renderSlaBadge(ticket)}

</div>

</div>


      <h1>
        ${escapeHTML(ticket.title)}
      </h1>


      <div class="detail-meta">

        <div class="detail-meta-item">
          <small>النوع</small>
          <strong>${escapeHTML(ticket.type || '—')}</strong>
        </div>


        <div class="detail-meta-item">
          <small>الإدارة</small>
          <strong>${escapeHTML(ticket.department || '—')}</strong>
        </div>


        <div class="detail-meta-item">
          <small>تاريخ الإنشاء</small>
          <strong>
            ${icon('clock')}
            ${escapeHTML(formatDateTime(ticket.createdAt))}
          </strong>
        </div>


        ${facts.map(
          fact => `
            <div class="detail-meta-item">
              <small>${fact.label}</small>
              <strong>${fact.value}</strong>
            </div>
          `
        ).join('')}

      </div>

    </section>
  `;
}

function renderTicketProgress(ticket) {
  const activeIndex =
    ticketStageIndex(ticket.status);

  return `
    <nav
      class="ticket-progress"
      aria-label="مراحل الطلب"
    >

      ${ticketStages.map(
        (stage, index) => {

          const stateClass =
            index < activeIndex
              ? 'is-complete'
              : index === activeIndex
                ? 'is-current'
                : '';

          const marker =
            index < activeIndex
              ? icon('check')
              : `<span>${index + 1}</span>`;

          return `
            <div
              class="ticket-stage ${stateClass}"
              ${
                index === activeIndex
                  ? 'aria-current="step"'
                  : ''
              }
            >

              <span class="ticket-stage-marker">
                ${marker}
              </span>

              <span class="ticket-stage-label">
                ${stage.label}
              </span>

            </div>
          `;
        }
      ).join('')}

    </nav>
  `;
}

function statCard(
  iconName,
  number,
  label,
  featured = false,
  tone = 'total'
) {
  return `
    <article
      class="stat-card ${featured ? 'featured' : ''}"
      data-tone="${escapeHTML(tone)}"
    >

      <span class="stat-icon">
        ${icon(iconName)}
      </span>

      <div>
        <strong>
          ${number}
        </strong>

        <span>
          ${label}
        </span>
      </div>

    </article>
  `;
}

function renderAttachment(ticket) {
  if (!ticket.attachment) {
    return '';
  }

  return `
    <a
      class="attachment"
      href="/support/attachment/${ticket.attachment.id}"
    >
      <span class="file-icon">
        ${icon('paperclip')}
      </span>

      <span class="attachment-info">
        <strong title="${escapeHTML(ticket.attachment.name || '')}">
          ${escapeHTML(ticket.attachment.name || '')}
        </strong>

        <small>
          تحميل المرفق
        </small>
      </span>
    </a>
  `;
}
function renderTimeline(items = []) {
  return `
    <ol class="timeline">

      ${items.map(
        item => `
          <li>

            <strong>
              ${escapeHTML(item.title || '')}
            </strong>

            <small>
  ${escapeHTML(
    formatDateTime(
      item.meta
    )
  )}
</small>
          </li>
        `
      ).join('')}

    </ol>
  `;
}

function renderChat(
  ticket,
  currentRole,
  canSend = true
) {
  const messages =
    Array.isArray(ticket.messages)
      ? ticket.messages
      : [];

  return `
    <section class="surface chat-card">

      <div class="surface-header">

        <h2>
          المحادثة داخل الطلب
        </h2>

      </div>

      <div
        class="chat-body"
        id="chat-body"
      >

        ${
          messages.length
            ? messages.map(
                message => `
                  <article
                    class="chat-message ${
                      message.sender === currentRole
                        ? 'mine'
                        : 'theirs'
                    }"
                  >

                    <strong class="chat-author">
                      ${escapeHTML(
                        message.name || ''
                      )}
                    </strong>

                    ${
                      message.text
                        ? `
                          <p class="chat-text">
                            ${escapeHTML(
                              message.text
                            )}
                          </p>
                        `
                        : ''
                    }

                    ${
                      (message.attachments || []).length
                        ? `
                          <div class="chat-attachments">

                            ${(message.attachments || [])
                              .map(
                                attachment => `
                                  <a
                                    class="chat-attachment"
                                    href="${escapeHTML(
                                      attachment.url || '#'
                                    )}"
                                    target="_blank"
                                    rel="noopener"
                                  >
                                    ${icon('paperclip')}

                                    <span>
                                      ${escapeHTML(
                                        attachment.name ||
                                        'مرفق'
                                      )}
                                    </span>

                                  </a>
                                `
                              )
                              .join('')}

                          </div>
                        `
                        : ''
                    }

                    <small class="chat-time">
                      ${escapeHTML(
                        message.time || ''
                      )}
                    </small>

                  </article>
                `
              ).join('')

            : `
                <div class="chat-empty">
                  لا توجد رسائل حتى الآن
                </div>
              `
        }

      </div>

      ${
        canSend
          ? `
            <div class="chat-composer">

              <button
                class="chat-attach"
                type="button"
                id="chat-attach"
                aria-label="إرفاق ملف"
              >
                ${icon('paperclip')}

                <span class="button-label">
                  إرفاق
                </span>
              </button>

              <input
                class="chat-input"
                id="chat-input"
                type="text"
                placeholder="اكتب رسالتك..."
                aria-label="نص الرسالة"
              >

              <button
                class="button chat-send"
                type="button"
                id="chat-send"
              >
                ${icon('send')}

                <span class="button-label">
                  إرسال
                </span>
              </button>

              <input
                id="chat-file"
                type="file"
                hidden
              >

            </div>
          `
          : ''
      }

    </section>
  `;
}

function scrollChatToBottom() {
  const chatBody =
    document.getElementById(
      'chat-body'
    );

  if (!chatBody) {
    return;
  }

  chatBody.scrollTo({
    top: chatBody.scrollHeight,
    behavior: 'smooth'
  });
}
function showToast(message, type = 'error') {
  const toast = document.getElementById('toast');

  if (!toast) return;

  window.clearTimeout(showToast.timer);

  const symbols = {
    success: '✓',
    error: '×',
    warning: '!'
  };

  toast.dataset.type = type;

  toast.setAttribute(
    'role',
    type === 'error' ? 'alert' : 'status'
  );

  toast.innerHTML = `
    <span
      class="toast-state-icon"
      aria-hidden="true"
    ></span>

    <span class="toast-message"></span>

    <span
      class="toast-progress"
      aria-hidden="true"
    ></span>
  `;

  toast.querySelector('.toast-state-icon').textContent =
    symbols[type];

  toast.querySelector('.toast-message').textContent =
    message ?? '';

  toast.hidden = false;

  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2000);
}
 async function loadTicketMessages(ticket) {
  try {
    const response = await fetch(
      `/support/ticket/messages?ticket_number=${encodeURIComponent(
        ticket.id
      )}`
    );

    const result = await response.json();

    if (
      !response.ok ||
      !result.success
    ) {
      showToast(
        result.message ||
        'تعذر تحميل المحادثة'
      );

      return false;
    }

    ticket.messages = (
      result.messages || []
    ).map(message => ({
      id: message.id,
      sender: message.mine
        ? 'support'
        : 'employee',
      name: message.author || '',
      text: message.text || '',
      time: formatDateTime(
        message.created_at
      ),
      attachments:
        message.attachments || []
    }));

    return true;

  } catch (error) {
    console.error(
      'Load manager chat error:',
      error
    );

    return false;
  }
}

function mountShell({
  role,
  active,
  navigate
}) {
  const isEmployee =
    role === 'employee';

  const items =
    isEmployee

      ? [
          {
            key: 'requests',
            label: 'الرئيسية'
          },
          {
            key: 'new',
            label: 'إنشاء طلب'
          }
        ]

      : [
          {
            key: 'dashboard',
            label: 'الرئيسية'
          },
          {
            key: 'performance',
            label: 'سجل الإنجاز'
          }
        ];

  const topbar =
    document.getElementById('topbar');

  if (!topbar) {
    return;
  }

  topbar.className =
    'topbar';

  topbar.innerHTML = `
    <div class="topbar-inner">

      <a
        class="brand"
        href="#${items[0].key}"
        data-route="${items[0].key}"
        aria-label="${escapeHTML(PORTAL_NAME)} — ${escapeHTML(BRAND_NAME)}"
      >

        ${
          BRAND_LOGO
            ? `
                <img
                  class="brand-logo"
                  src="${escapeHTML(BRAND_LOGO)}"
                  alt="${escapeHTML(BRAND_NAME)}"
                >
              `
            : ''
        }
         <span class="brand-text">
    <b>
      ${escapeHTML(PORTAL_NAME)}
    </b>

    <small>
      ${escapeHTML(BRAND_NAME)}
    </small>
  </span>
    

      </a>

      <nav
        class="main-nav"
        aria-label="التنقل الرئيسي"
      >

        ${items.map(
          item => `
            <a
              href="#${item.key}"
              class="nav-link ${
                active === item.key
                  ? 'active'
                  : ''
              }"
              data-route="${item.key}"
              ${
                active === item.key
                  ? 'aria-current="page"'
                  : ''
              }
            >
              <span>
                ${item.label}
              </span>
            </a>
          `
        ).join('')}

      </nav>

    <div class="nav-actions">

  <button
    class="icon-button"
    id="notifications-button"
    type="button"
    aria-label="الإشعارات"
    aria-expanded="false"
  >
    ${icon('bell')}

    <span
      class="notification-count"
      id="notification-count"
    >
      0
    </span>
  </button>

  <section
    class="notifications-panel"
    id="notifications-panel"
    aria-label="الإشعارات"
    hidden
  ></section>

</div>
    </div>
  `;


  topbar
    .querySelector('.brand-logo')
    ?.addEventListener(
      'error',
      event => {
        event.currentTarget.remove();
      }
    );

  topbar
    .querySelectorAll(
      '[data-route]'
    )
    .forEach(
      link => {

        link.addEventListener(
          'click',
          event => {

            event.preventDefault();

            navigate(
              link.dataset.route
            );
          }
        );

      }
    );
}


/*
  State
  الطلبات تأتي من Odoo.
 */
const state = {
  tickets: []
};

const CURRENT_SUPPORT =
  app?.dataset.supportName
  || 'مسؤول الدعم';

const initialRoute =
  readRoute('dashboard');

let currentRoute =
  initialRoute.route;

let selectedTicketId =
  initialRoute.ticketId;


/*
 * Navigation
 */
function navigate(
  route,
  ticketId = null
) {
  currentRoute =
    route;

  selectedTicketId =
    ticketId;

  history.replaceState(
    null,
    '',
    `#${route}${
      ticketId
        ? `/${ticketId}`
        : ''
    }`
  );

  render();
}


/*
 * Load tickets from Odoo Database
 */
async function loadManagerTickets() {
  try {

    const response =
      await fetch(
        '/support/manager/tickets',
        {
          method: 'GET',
          headers: {
            'Accept':
              'application/json'
          }
        }
      );

    const result =
      await response.json();

    if (
      !response.ok
      || !result.success
    ) {

      console.error(
        'Manager tickets error:',
        result.message
      );

      showToast(
        result.message
        || 'تعذر تحميل طلبات الدعم'
      );

      return false;
    }

    state.tickets =
      Array.isArray(
        result.tickets
      )
        ? result.tickets
        : [];

    return true;

  } catch (error) {

    console.error(
      'Load manager tickets error:',
      error
    );

    showToast(
      'حدث خطأ أثناء تحميل طلبات الدعم'
    );

    return false;
  }
}
async function markNotificationRead(
  notificationId = null
) {
  try {
    const response = await fetch(
      '/support/notifications/read',
      {
        method: 'POST',
        headers: {
          'Content-Type':
            'application/json'
        },
        body: JSON.stringify({
          notification_id:
            notificationId
        })
      }
    );

    const result =
      await response.json();

    return (
      response.ok &&
      result.success
    );

  } catch (error) {
    console.error(
      'Mark notification read error:',
      error
    );

    return false;
  }
}

function bindNotifications(
  state,
  role,
  openTicket
) {
  const button =
    document.getElementById(
      'notifications-button'
    );

  const panel =
    document.getElementById(
      'notifications-panel'
    );

  const count =
    document.getElementById(
      'notification-count'
    );

  if (
    !button ||
    !panel ||
    !count
  ) {
    return;
  }

  const draw = () => {
    const items =
      state.notifications?.[
        role
      ] || [];

    const unread =
  items.filter(
    item =>
      !item.read
  ).length;

count.textContent =
  unread;

count.hidden =
  unread === 0;

    panel.innerHTML = `
      <div class="panel-head">

        <strong>
          الإشعارات
        </strong>

        <button
          class="text-button"
          id="mark-read"
          type="button"
        >
          تحديد الكل كمقروء
        </button>

      </div>

      <div
        class="notification-list"
      >

        ${
          items.length
            ? items
                .map(
                  item => `
                    <button
                      type="button"
                      class="notification-item ${
                        item.read
                          ? ''
                          : 'unread'
                      }"
                      data-notification="${item.id}"
                    >

                      <span
                        class="notification-icon"
                      >
                        ${icon('bell')}
                      </span>

                      <span>

                        <strong>
                          ${escapeHTML(
                            item.title
                          )}
                        </strong>

                        <p>
                          ${escapeHTML(
                            item.text
                          )}
                        </p>

                        <small>
                          ${escapeHTML(
                            item.time
                          )}
                        </small>

                      </span>

                    </button>
                  `
                )
                .join('')

            : `
              <div class="empty-state">
                لا توجد إشعارات
              </div>
            `
        }

      </div>
    `;
    const markAllButton =
      panel.querySelector(
        '#mark-read'
      );

    if (markAllButton) {
      markAllButton.addEventListener(
        'click',
        async event => {
          event.stopPropagation();

          const success =
            await markNotificationRead();

          if (!success) {
            showToast(
              'تعذر تحديد الإشعارات كمقروءة'
            );
            return;
          }

          items.forEach(item => {
            item.read = true;
          });

          draw();
        }
      );
    }




    panel
  .querySelectorAll(
    '[data-notification]'
  )
  .forEach(
    itemButton => {

      itemButton
        .addEventListener(
          'click',
          async () => {

            const item =
              items.find(
                entry =>
                  entry.id ===
                  itemButton.dataset.notification
              );

            if (!item) {
              return;
            }

            await markNotificationRead(
              item.id
            );

            item.read = true;

            panel.hidden = true;

            openTicket(
              item.ticketId
            );
          }
        );
    }
  );
 };
  draw();

  button.addEventListener(
    'click',
    () => {

      panel.hidden =
        !panel.hidden;

      button.setAttribute(
        'aria-expanded',
        String(
          !panel.hidden
        )
      );
    }
  );

  if (
    !document.body.dataset
      .notificationsOutsideBound
  ) {
    document.body.dataset
      .notificationsOutsideBound =
        'true';

    document.addEventListener(
      'click',
      event => {

        if (
          !event.target.closest(
            '.nav-actions'
          )
        ) {
          const currentPanel =
            document.getElementById(
              'notifications-panel'
            );

          if (
            currentPanel
          ) {
            currentPanel.hidden =
              true;
          }
        }
      }
    );
  }
}

/*
 * Main Render
 */
async function render() {
await loadManagerTickets();
await loadSupportNotifications();


  const routeKey =
    currentRoute === 'detail'
      ? 'dashboard'
      : currentRoute;

  mountShell({
    role: 'support',
    active: routeKey,
    navigate
  });

   bindNotifications(
    state,
    'support',
    id => navigate('detail', id)
  );

  if (
    currentRoute === 'detail'
  ) {

    renderDetail(
      selectedTicketId
    );

  } else if (
    currentRoute === 'performance'
  ) {

    renderPerformance();

  } else {

    renderDashboard();

  }
}


/*
 * Dashboard
 */
function renderDashboard() {

  app.innerHTML = `

    <header class="page-head">

      <div>

        <h1>
          لوحة الدعم الفني
        </h1>

      </div>

    </header>


    <section
      class="stats-grid"
      aria-label="ملخص طلبات الدعم"
    >

      ${statCard(
        'tickets',
        state.tickets.length,
        'إجمالي الطلبات'
      )}


      ${statCard(
        'inbox',
        state.tickets.filter(
          ticket =>
            ticket.status === 'جديد'
        ).length,
        'بانتظار الاستلام',
        true,
        'new'
      )}


      ${statCard(
        'clock',
        state.tickets.filter(
          ticket =>
            ticket.status
            === 'قيد المعالجة'
        ).length,
        'قيد المعالجة',
        false,
        'processing'
      )}


      ${statCard(
        'check',
        state.tickets.filter(
          ticket =>
            ticket.status === 'مغلق'
        ).length,
        'طلبات مغلقة',
        false,
        'closed'
      )}

    </section>


    <section
      class="surface requests-surface"
    >

      <div class="surface-header">

        <h2>
          طلبات الدعم
        </h2>

        <div
          class="filter-control search-box"
        >

          ${icon('search')}

          <input
            class="field-control search-control"
            id="support-search"
            type="search"
            placeholder="ابحث برقم الطلب أو الموضوع"
            aria-label="البحث في طلبات الدعم"
          >

        </div>


        <div
          class="filter-control status-filter-box"
        >

          <select
            class="field-control"
            id="support-status"
            aria-label="تصفية حسب الحالة"
          >

            <option>
              كل الحالات
            </option>

            <option>
              جديد
            </option>

            <option>
              قيد المعالجة
            </option>
            <option>
            معلق مؤقتًا
            </option>

            <option>
              بانتظار تأكيد الموظف
            </option>

            <option>
              مغلق
            </option>

          </select>

        </div>

      </div>


      <div
        class="table-wrap requests-table-wrap"
      >

        <table
          class="data-table requests-table support-requests-table"
        >

          <colgroup>
            <col class="col-number">
            <col class="col-request">
            <col class="col-requester">
            <col class="col-department">
            <col class="col-status">
            <col class="col-assignee">
            <col class="col-priority">
            <col class="col-action">
          </colgroup>


          <thead>

            <tr>
              <th>رقم الطلب</th>
              <th>موضوع الطلب</th>
              <th>صاحب الطلب</th>
              <th>الإدارة</th>
              <th>الحالة</th>
              <th>مسؤول الدعم</th>
              <th>الأولوية</th>
              <th>الإجراء</th>
            </tr>

          </thead>


          <tbody
            id="support-rows"
          ></tbody>

        </table>

      </div>


      <div
        class="requests-pagination"
        id="support-pagination"
      ></div>

    </section>
  `;


  document
    .getElementById(
      'support-search'
    )
    .addEventListener(
      'input',
      () => {
        supportRequestsPage = 1;
        drawSupportRows();
      }
    );


  document
    .getElementById(
      'support-status'
    )
    .addEventListener(
      'change',
      () => {
        supportRequestsPage = 1;
        drawSupportRows();
      }
    );


  drawSupportRows();
}


/*
 * Draw Support Requests
 * ١٠ صفوف في الصفحة الواحدة، تمامًا كجدول طلبات الموظف
 */
let supportRequestsPage = 1;

const SUPPORT_PAGE_SIZE = 10;

function drawSupportRows() {

  const searchElement =
    document.getElementById(
      'support-search'
    );

  const statusElement =
    document.getElementById(
      'support-status'
    );

  const rows =
    document.getElementById(
      'support-rows'
    );


  if (
    !searchElement
    || !statusElement
    || !rows
  ) {
    return;
  }


  const query =
    searchElement.value
      .trim()
      .toLowerCase();


  const filter =
    statusElement.value;


  const tickets =
    state.tickets.filter(
      ticket => {

        const searchText =
          `${
            ticket.id
          } ${
            ticket.title
          } ${
            ticket.requester
          }`
            .toLowerCase();


        const matchesSearch =
          searchText.includes(
            query
          );


        const matchesStatus =
          filter === 'كل الحالات'
          || ticket.status === filter;


        return (
          matchesSearch
          && matchesStatus
        );
      }
    );


  const totalPages =
    Math.max(
      1,
      Math.ceil(
        tickets.length /
        SUPPORT_PAGE_SIZE
      )
    );


  if (
    supportRequestsPage >
    totalPages
  ) {
    supportRequestsPage =
      totalPages;
  }


  const startIndex =
    (
      supportRequestsPage - 1
    ) * SUPPORT_PAGE_SIZE;


  const pageTickets =
    tickets.slice(
      startIndex,
      startIndex +
      SUPPORT_PAGE_SIZE
    );


  rows.innerHTML =
    pageTickets.length

      ? pageTickets.map(
          ticket => {

            const canClaim =
              ticket.status === 'جديد'
              && !ticket.assignee;


            return `
              <tr>

                <td
                  data-label="رقم الطلب"
                >

                  <span class="request-code">
                    ${escapeHTML(
                      ticket.id
                    )}
                  </span>

                </td>


                <td
                  class="request-title"
                  data-label="موضوع الطلب"
                >

                  <strong>
                    ${escapeHTML(
                      ticket.title
                    )}
                  </strong>

                  <small>
                    ${escapeHTML(
                      ticket.type || ''
                    )}
                  </small>

                </td>


                <td
                  data-label="صاحب الطلب"
                >

                  ${escapeHTML(
                    ticket.requester || ''
                  )}

                </td>


                <td
                  data-label="الإدارة"
                >

                  ${escapeHTML(
                    ticket.department
                    || '—'
                  )}

                </td>


                <td
                  data-label="الحالة"
                >

                  ${statusBadge(
                    ticket.status
                  )}

                </td>


                <td
                  data-label="مسؤول الدعم"
                >

                  ${escapeHTML(
                    ticket.assignee
                    || 'غير مسند'
                  )}

                </td>


                <td
                  data-label="الأولوية"
                >

                  ${priorityBadge(
                    ticket.priority
                  )}

                </td>


                <td
                  class="row-actions-cell"
                >

                  <div class="row-actions">

                    <button
                      class="button secondary small"
                      type="button"
                      data-view="${ticket.id}"
                    >
                      عرض الطلب
                    </button>


                    ${
                      canClaim

                        ? `
                            <button
                              class="button small"
                              type="button"
                              data-claim="${ticket.id}"
                            >
                              استلام الطلب
                            </button>
                          `

                        : ''
                    }

                  </div>

                </td>

              </tr>
            `;
          }
        ).join('')

      : `
          <tr>

            <td colspan="8">

              <div class="empty-state">

                ${icon('inbox')}

                <div>
                  لا توجد طلبات مطابقة
                </div>

              </div>

            </td>

          </tr>
        `;


  rows
    .querySelectorAll(
      '[data-view]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => navigate(
            'detail',
            button.dataset.view
          )
        );

      }
    );


  rows
    .querySelectorAll(
      '[data-claim]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => claimTicket(
            button.dataset.claim
          )
        );

      }
    );


  drawSupportPagination(
    totalPages
  );
}


/*
 * ترقيم لوحة الدعم — نفس شكل وسلوك ترقيم واجهة الموظف
 */
function drawSupportPagination(totalPages) {

  const pagination =
    document.getElementById(
      'support-pagination'
    );


  if (!pagination) {
    return;
  }


  pagination.innerHTML =
    totalPages > 1

      ? `
          <div
            class="requests-pagination-inner"
          >

            <button
              type="button"
              data-page-action="prev"
              ${
                supportRequestsPage === 1
                  ? 'disabled'
                  : ''
              }
            >
              السابق
            </button>


            ${Array.from(
              {
                length: totalPages
              },
              (_, index) =>
                index + 1
            )
              .map(
                page => `
                  <button
                    type="button"
                    class="${
                      page ===
                      supportRequestsPage
                        ? 'active'
                        : ''
                    }"
                    data-page="${page}"
                    ${
                      page ===
                      supportRequestsPage
                        ? 'aria-current="page"'
                        : ''
                    }
                  >
                    ${page}
                  </button>
                `
              )
              .join('')}


            <button
              type="button"
              data-page-action="next"
              ${
                supportRequestsPage ===
                totalPages
                  ? 'disabled'
                  : ''
              }
            >
              التالي
            </button>

          </div>
        `

      : '';


  pagination
    .querySelectorAll(
      '[data-page]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            supportRequestsPage =
              Number(
                button.dataset.page
              );

            drawSupportRows();
          }
        );

      }
    );


  pagination
    .querySelector(
      '[data-page-action="prev"]'
    )
    ?.addEventListener(
      'click',
      () => {

        if (
          supportRequestsPage > 1
        ) {
          supportRequestsPage -= 1;

          drawSupportRows();
        }

      }
    );


  pagination
    .querySelector(
      '[data-page-action="next"]'
    )
    ?.addEventListener(
      'click',
      () => {

        if (
          supportRequestsPage <
          totalPages
        ) {
          supportRequestsPage += 1;

          drawSupportRows();
        }

      }
    );
}


/*
 * Claim Ticket
 */
async function claimTicket(id) {

  const ticket =
    getTicket(
      state,
      id
    );


  if (!ticket) {

    showToast(
      'الطلب غير موجود'
    );

    return;
  }


  if (
    ticket.assignee
    || ticket.status !== 'جديد'
  ) {

   showToast(
  'هذا الطلب تم استلامه مسبقًا',
  'warning'
);

    return;
  }


  try {

    const response =
      await fetch(
        '/support/ticket/claim',
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json'
          },

          body: JSON.stringify({
            ticket_number: id
          })
        }
      );


    const result =
      await response.json();


    if (
      !response.ok
      || !result.success
    ) {

      showToast(
        result.message
        || 'تعذر استلام الطلب'
      );

      return;
    }


    showToast(
  `تم إسناد الطلب ${id} إليك وبدأت معالجته`,
  'success'
);


    await loadManagerTickets();


    navigate(
      'detail',
      id
    );


  } catch (error) {

    console.error(
      'Claim ticket error:',
      error
    );


    showToast(
      'حدث خطأ أثناء استلام الطلب'
    );

  }
}
async function loadSupportNotifications() {
  try {
    const response = await fetch(
      '/support/notifications',
      {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      }
    );

    const result = await response.json();

    if (!response.ok || !result.success) {
      console.error(
        'Notifications error:',
        result.message
      );

      return false;
    }

    if (!state.notifications) {
      state.notifications = {};
    }

    state.notifications.support = (
      result.notifications || []
    ).map(notification => ({
      id: String(notification.id),
      title: notification.title,
      text: notification.message,
      time: formatDateTime(notification.created_at),
      read: notification.is_read,
      ticketId: notification.ticket_number
    }));

    return true;

  } catch (error) {
    console.error(
      'Load notifications error:',
      error
    );

    return false;
  }
}

/*
 * Ticket Detail
 */
async function renderDetail(id) {

  const ticket =
    getTicket(
      state,
      id
    );

  if (!ticket) {
    return navigate(
      'dashboard'
    );
  }

  await loadTicketMessages(
    ticket
  );

  if (supportBus) {
    supportBus.addChannel(
      `support_ticket_${ticket.id}`
    );
  }

  const canProcess =
  ticket.assignee_id === CURRENT_SUPPORT_ID &&
  ticket.status === 'قيد المعالجة';
  const canChat =
  ticket.assignee_id ===
    CURRENT_SUPPORT_ID &&
  ticket.status !==
    'مغلق';

  app.innerHTML = `
   

  <div class="record-card">

      ${renderTicketHero(ticket, [
        {
          label: 'صاحب الطلب',
          value: escapeHTML(ticket.requester || '—')
        },
        {
        label: 'مسؤول الدعم',
        value: escapeHTML(
          ticket.assignee ||
          'لم يتم الإسناد بعد'
        )
      },
      {
        label: 'الأولوية',
        value: priorityBadge(ticket.priority)
      }
    ])}

      ${renderTicketProgress(ticket)}

    </div>

    <div class="detail-stack">

      <section class="surface">

        <div class="content-section">

          <h2>
            تفاصيل المشكلة
          </h2>

          <p class="problem-copy">${escapeHTML(ticket.description)}</p>

          ${renderAttachment(ticket)}

        </div>


        ${
          ticket.solution

            ? `
                <div
                  class="content-section workflow-card"
                >

                  <h2>
                    الحل المسجل
                  </h2>

                  <div class="solution-box">

                    <p class="solution-text">${escapeHTML(ticket.solution)}</p>

                    <small class="solution-meta">${escapeHTML(ticket.assignee || '')} — ${escapeHTML(formatDateTime(ticket.solutionAt))}</small>

                  </div>

                </div>
              `

            : ''
        }


        ${renderProcessing(
          ticket,
          canProcess
        )}

      </section>


      ${renderChat(
        ticket,
        'support',
        canChat
      )}


      <section
        class="surface timeline-surface"
        aria-label="سجل المتابعة"
      >

        <div class="content-section">

          <h2>
            سجل المتابعة
          </h2>

          ${renderTimeline(
            ticket.timeline || []
          )}

        </div>

      </section>

      

    </div>
  `;

  document
    .getElementById(
      'claim-from-detail'
    )
    ?.addEventListener(
      'click',
      () => claimTicket(
        ticket.id
      )
    );


  document
    .getElementById(
      'send-solution'
    )
    ?.addEventListener(
      'click',
      () => sendSolution(
        ticket
      )
    );
    scrollChatToBottom();
    bindChat({
  ticket
});

const holdButton =
  document.getElementById(
    'hold-ticket'
  );

if (holdButton) {

  holdButton.addEventListener(
    'click',
    () => holdTicket(ticket)
  );
}


const resumeButton =
  document.getElementById(
    'resume-ticket'
  );

if (resumeButton) {

  resumeButton.addEventListener(
    'click',
    () => resumeTicket(ticket)
  );
}


}

function bindChat({
  ticket
}) {
  const input =
    document.getElementById(
      'chat-input'
    );

  const send =
    document.getElementById(
      'chat-send'
    );

  const file =
    document.getElementById(
      'chat-file'
    );

  if (
    !input ||
    !send
  ) {
    return;
  }

  const submit =
    async () => {

      const text =
        input.value.trim();

      const attachment =
        file?.files?.[0] ||
        null;

      if (
        !text &&
        !attachment
      ) {
        return;
      }

      const formData =
        new FormData();

      formData.append(
        'ticket_number',
        ticket.id
      );

      formData.append(
        'message',
        text
      );

      if (attachment) {
        formData.append(
          'attachment',
          attachment
        );
      }

      send.disabled = true;

      try {
        const response =
          await fetch(
            '/support/ticket/message/send',
            {
              method: 'POST',
              body: formData
            }
          );

        const result =
          await response.json();

        if (
          !response.ok ||
          !result.success
        ) {
          showToast(
            result.message ||
            'تعذر إرسال الرسالة'
          );

          return;
        }

        input.value = '';

        if (file) {
          file.value = '';
        }

        await renderDetail(
          ticket.id
        );

      } catch (error) {
        console.error(
          'Send manager chat error:',
          error
        );

        showToast(
          'حدث خطأ أثناء إرسال الرسالة'
        );

      } finally {
        send.disabled = false;
      }
    };

  send.addEventListener(
    'click',
    submit
  );

  input.addEventListener(
    'keydown',
    event => {
      if (
        event.key === 'Enter'
      ) {
        event.preventDefault();
        submit();
      }
    }
  );

  document
    .getElementById(
      'chat-attach'
    )
    ?.addEventListener(
      'click',
      () => {
        file?.click();
      }
    );
}

/*
 * Processing
 */
function renderProcessing(
  ticket,
  canProcess
) {

  if (
    ticket.status === 'جديد'
    && !ticket.assignee
  ) {

    return `
      <div
        class="content-section workflow-card"
      >

        <h2>
          معالجة الطلب
        </h2>

        <button
          class="button"
          type="button"
          id="claim-from-detail"
        >
          استلام الطلب
        </button>

      </div>
    `;
  }


  /*
   * الطلب معلق مؤقتًا
   */
  if (
    ticket.status === 'معلق مؤقتًا'
  ) {

    const reasons = {
      waiting_employee:
        'بانتظار الموظف',

      waiting_approval:
        'بانتظار موافقة',

      waiting_internal:
        'بانتظار جهة داخلية',

      scheduled:
        'بانتظار موعد مجدول'
    };


    const reason =
      reasons[
        ticket.sla_pause_reason
      ]
      || 'غير محدد';


    return `
      <div
        class="content-section workflow-card"
      >

        <h2>
          الطلب معلق مؤقتًا
        </h2>


        <div class="action-callout">

          <h3>
            تم إيقاف المعالجة مؤقتًا
          </h3>

          <p>
            السبب:
            <strong>
              ${escapeHTML(reason)}
            </strong>
          </p>

        </div>


        <div class="form-actions">

          <span></span>

          <button
            class="button"
            type="button"
            id="resume-ticket"
          >
            استئناف المعالجة
          </button>

        </div>

      </div>
    `;
  }


  /*
   * الطلب تحت المعالجة
   */
  if (canProcess) {

    return `
      <div
        class="content-section workflow-card"
      >

        <h2>
          توثيق الحل
        </h2>


        <div class="form-field">

          <label for="solution">

            كيف تم حل المشكلة؟

            <span class="required"></span>

          </label>


          <textarea
            class="field-control"
            id="solution"
            placeholder="اكتب الإجراء المنفذ والنتيجة التي تم التحقق منها"
          >${escapeHTML(
            ticket.solution || ''
          )}</textarea>

        </div>


        <div class="form-field">

          <label for="hold-reason">
            تعليق الطلب مؤقتًا
          </label>

          <select
            class="field-control"
            id="hold-reason"
          >
            <option value="">
              اختر سبب التعليق
            </option>

            <option value="waiting_employee">
              بانتظار الموظف
            </option>

            <option value="waiting_approval">
              بانتظار موافقة
            </option>

            <option value="waiting_internal">
              بانتظار جهة داخلية
            </option>

            <option value="scheduled">
              بانتظار موعد مجدول
            </option>

          </select>

        </div>


        <div class="form-actions">

          <button
            class="button button-secondary"
            type="button"
            id="hold-ticket"
          >
            تعليق الطلب
          </button>


          <button
            class="button"
            type="button"
            id="send-solution"
          >

            ${icon('send')}

            إرسال الحل للموظف

          </button>

        </div>

      </div>
    `;
  }


  if (
    ticket.status
    === 'بانتظار تأكيد الموظف'
  ) {

    return `
      <div class="content-section">

        <div class="action-callout">

          <h3>
            بانتظار تأكيد صاحب الطلب
          </h3>

          <p>
            يُغلق الطلب تلقائياً بعد تأكيد الموظف
            أن الحل نجح، أو يعود للمعالجة إذا أفاد
            باستمرار المشكلة
          </p>

        </div>

      </div>
    `;
  }


  return '';
}

/*
 Send Solution
 */
async function sendSolution(ticket) {

  const solutionElement =
    document.getElementById(
      'solution'
    );


  if (!solutionElement) {
    return;
  }


  const solution =
    solutionElement.value
      .trim();


  if (!solution) {

    showToast(
  'اكتب كيف تم حل المشكلة قبل إرسال الحل',
  'warning'
);
    return;
  }


  try {

    const response =
      await fetch(
        '/support/ticket/solution',
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json'
          },

          body: JSON.stringify({
            ticket_number:
              ticket.id,
            solution
          })
        }
      );


    const result =
      await response.json();


    if (
      !response.ok
      || !result.success
    ) {

      showToast(
        result.message
        || 'تعذر إرسال الحل'
      );

      return;
    }


  showToast(
  'تم إرسال الحل لصاحب الطلب',
  'success'
);

    await loadManagerTickets();


    navigate(
      'detail',
      ticket.id
    );


  } catch (error) {

    console.error(
      'Send solution error:',
      error
    );


    showToast(
      'حدث خطأ أثناء إرسال الحل'
    );

  }
}

async function holdTicket(ticket) {

  const reasonElement =
    document.getElementById(
      'hold-reason'
    );

  if (!reasonElement) {
    return;
  }


  const reason =
    reasonElement.value;


  if (!reason) {

    showToast(
      'اختاري سبب تعليق الطلب',
      'warning'
    );

    return;
  }


  try {

    const response =
      await fetch(
        '/support/ticket/hold',
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json'
          },

          body: JSON.stringify({
            ticket_number:
              ticket.id,
            reason
          })
        }
      );


    const result =
      await response.json();


    if (
      !response.ok
      || !result.success
    ) {

      showToast(
        result.message
        || 'تعذر تعليق الطلب',
        'warning'
      );

      return;
    }


  showToast(
  'تم تعليق الطلب مؤقتًا',
  'success'
);

await loadManagerTickets();

navigate(
  'detail',
  ticket.id
);

  } catch (error) {

    showToast(
      'حدث خطأ أثناء تعليق الطلب',
      'warning'
    );
  }
}


async function resumeTicket(ticket) {

  try {

    const response =
      await fetch(
        '/support/ticket/resume',
        {
          method: 'POST',

          headers: {
            'Content-Type':
              'application/json'
          },

          body: JSON.stringify({
            ticket_number:
              ticket.id
          })
        }
      );


    const result =
      await response.json();


    if (
      !response.ok
      || !result.success
    ) {

      showToast(
        result.message
        || 'تعذر استئناف معالجة الطلب',
        'warning'
      );

      return;
    }


    showToast(
      'تم استئناف معالجة الطلب',
      'success'
    );


navigate(
  'detail',
  ticket.id
);

  } catch (error) {

    showToast(
      'حدث خطأ أثناء استئناف الطلب',
      'warning'
    );
  }
}
 function getPlatformSlaStats(tickets) {

  let successful = 0;
  let failed = 0;

  tickets.forEach(ticket => {

    [
      ticket.sla_response_status,
      ticket.sla_resolution_status
    ].forEach(status => {

      if (status === 'successful') {
        successful += 1;
      }

      if (status === 'failed') {
        failed += 1;
      }

    });

  });

  const total =
    successful + failed;

  const compliance =
    total
      ? Math.round(
          (
            successful / total
          ) * 100
        )
      : 0;

  return {
    successful,
    failed,
    total,
    compliance
  };
}


function renderSlaDonut(tickets) {

  const stats =
    getPlatformSlaStats(
      tickets
    );

  return `
    <article class="analytics-card">

      <div class="analytics-card-head">

        <div>

          <h3>
            نسبة الالتزام بالـ SLA
          </h3>

          <p>
            الالتزام العام بالاستجابة والحل
          </p>

        </div>

      </div>


      <div class="sla-donut-wrap">

        <div
          class="sla-donut"
          style="
            --sla-value:
            ${stats.compliance}
          "
        >

          <div class="sla-donut-center">

            <strong>
              ${stats.compliance}%
            </strong>

            <span>
              ملتزم
            </span>

          </div>

        </div>


        <div class="sla-donut-legend">

          <div>

            <span class="legend-dot is-success"></span>

            <span>
              محقق
            </span>

            <strong>
              ${stats.successful}
            </strong>

          </div>


          <div>

            <span class="legend-dot is-failed"></span>

            <span>
              متجاوز
            </span>

            <strong>
              ${stats.failed}
            </strong>

          </div>

        </div>

      </div>

    </article>
  `;
}


function renderSlaBarChart(tickets) {

  const categories = {};

  tickets.forEach(ticket => {

    const category =
      ticket.type || 'غير مصنف';

    if (!categories[category]) {

      categories[category] = {
        successful: 0,
        failed: 0
      };

    }

    const hasFailed =
      ticket.sla_response_status === 'failed'
      || ticket.sla_resolution_status === 'failed';

    const hasSuccessful =
      !hasFailed
      && (
        ticket.sla_response_status === 'successful'
        || ticket.sla_resolution_status === 'successful'
      );

    if (hasFailed) {
      categories[
        category
      ].failed += 1;
    }

    else if (hasSuccessful) {
      categories[
        category
      ].successful += 1;
    }

  });


  const entries =
    Object.entries(
      categories
    );


  const maxValue =
    Math.max(
      1,
      ...entries.map(
        ([, values]) =>
          Math.max(
            values.successful,
            values.failed
          )
      )
    );


  return `
    <article class="analytics-card">

      <div class="analytics-card-head">

        <div>

          <h3>
            SLA حسب نوع الطلب
          </h3>

          <p>
            مقارنة الطلبات الملتزمة والمتجاوزة
          </p>

        </div>

      </div>


      <div class="sla-bar-chart">

        ${
          entries.length

            ? entries.map(
                ([category, values]) => `
                  <div class="sla-bar-row">

                    <span class="sla-bar-label">
                      ${escapeHTML(category)}
                    </span>


                    <div class="sla-bar-values">

                      <div class="sla-bar-line">

                        <span>
                          محقق
                        </span>

                        <div class="sla-bar-track">

                          <i
                            class="sla-bar-fill is-success"
                            style="
                              width:
                              ${
                                (
                                  values.successful
                                  / maxValue
                                ) * 100
                              }%
                            "
                          ></i>

                        </div>

                        <strong>
                          ${values.successful}
                        </strong>

                      </div>


                      <div class="sla-bar-line">

                        <span>
                          متجاوز
                        </span>

                        <div class="sla-bar-track">

                          <i
                            class="sla-bar-fill is-failed"
                            style="
                              width:
                              ${
                                (
                                  values.failed
                                  / maxValue
                                ) * 100
                              }%
                            "
                          ></i>

                        </div>

                        <strong>
                          ${values.failed}
                        </strong>

                      </div>

                    </div>

                  </div>
                `
              ).join('')

            : `
                <div class="analytics-empty">
                  لا توجد بيانات كافية
                </div>
              `
        }

      </div>

    </article>
  `;
}


function renderSlaTrend(tickets) {

  const now =
    new Date();

  const months = [];

  for (
    let offset = 5;
    offset >= 0;
    offset -= 1
  ) {

    const date =
      new Date(
        now.getFullYear(),
        now.getMonth() - offset,
        1
      );

    months.push({
      key:
        `${date.getFullYear()}-${
          String(
            date.getMonth() + 1
          ).padStart(
            2,
            '0'
          )
        }`,

      label:
        new Intl.DateTimeFormat(
          'ar-SA-u-ca-gregory-nu-latn',
          {
            month: 'short'
          }
        ).format(date),

      successful: 0,
      failed: 0
    });

  }


  tickets.forEach(ticket => {

    if (!ticket.createdAt) {
      return;
    }

    const date =
      new Date(
        ticket.createdAt
      );

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return;
    }

    const key =
      `${date.getFullYear()}-${
        String(
          date.getMonth() + 1
        ).padStart(
          2,
          '0'
        )
      }`;

    const month =
      months.find(
        item =>
          item.key === key
      );

    if (!month) {
      return;
    }


    [
      ticket.sla_response_status,
      ticket.sla_resolution_status
    ].forEach(status => {

      if (status === 'successful') {
        month.successful += 1;
      }

      if (status === 'failed') {
        month.failed += 1;
      }

    });

  });


  const values =
    months.map(month => {

      const total =
        month.successful
        + month.failed;

      return total
        ? Math.round(
            (
              month.successful
              / total
            ) * 100
          )
        : 0;

    });


  const width = 600;
  const height = 180;
  const padding = 20;


  const points =
    values.map(
      (value, index) => {

        const x =
          padding
          + (
            index
            / Math.max(
              values.length - 1,
              1
            )
          )
          * (
            width
            - padding * 2
          );

        const y =
          height
          - padding
          - (
            value / 100
          )
          * (
            height
            - padding * 2
          );

        return {
          x,
          y,
          value
        };

      }
    );


  return `
    <article
      class="
        analytics-card
        analytics-card-wide
      "
    >

      <div class="analytics-card-head">

        <div>

          <h3>
            اتجاه الالتزام بالـ SLA
          </h3>

          <p>
            نسبة الالتزام خلال آخر 6 أشهر
          </p>

        </div>

      </div>


      <div class="sla-line-chart">

        <svg
          viewBox="0 0 ${width} ${height}"
          preserveAspectRatio="none"
          aria-label="اتجاه الالتزام بالـ SLA"
        >

          <polyline
            class="sla-line-path"
            points="${
              points.map(
                point =>
                  `${point.x},${point.y}`
              ).join(' ')
            }"
          ></polyline>


          ${
            points.map(
              point => `
                <circle
                  class="sla-line-point"
                  cx="${point.x}"
                  cy="${point.y}"
                  r="4"
                ></circle>
              `
            ).join('')
          }

        </svg>


        <div class="sla-line-labels">

          ${
            months.map(
              (month, index) => `
                <span>

                  <small>
                    ${escapeHTML(
                      month.label
                    )}
                  </small>

                  <strong>
                    ${values[index]}%
                  </strong>

                </span>
              `
            ).join('')
          }

        </div>

      </div>

    </article>
  `;
}


function renderPlatformCharts(
  tickets
) {

  return `
    <section class="platform-analytics">

      <div class="performance-section-head">

        <h2>
          أداء المنصة
        </h2>

      </div>


      <div class="platform-charts-grid">

        ${renderSlaDonut(
          tickets
        )}

        ${renderSlaBarChart(
          tickets
        )}

        ${renderSlaTrend(
          tickets
        )}

      </div>

    </section>
  `;
}
/*
 * Performance
 */
let performanceCurrentPage = 1;

const PERFORMANCE_PAGE_SIZE = 10;

function renderPerformance() {

 const owned = state.tickets.filter(
  ticket => ticket.assignee_id === CURRENT_SUPPORT_ID
);
  const closed =
    owned.filter(
      ticket =>
        ticket.status === 'مغلق'
    );

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        closed.length /
        PERFORMANCE_PAGE_SIZE
      )
    );

  if (
    performanceCurrentPage >
    totalPages
  ) {
    performanceCurrentPage =
      totalPages;
  }

  const startIndex =
    (
      performanceCurrentPage - 1
    ) * PERFORMANCE_PAGE_SIZE;

  const pageClosed =
    closed.slice(
      startIndex,
      startIndex +
      PERFORMANCE_PAGE_SIZE
    );

  const ratings =
    closed
      .filter(
        ticket =>
          ticket.rating
      )
      .map(
        ticket =>
          ticket.rating.value
      );

  const average =
    ratings.length
      ? (
          ratings.reduce(
            (sum, value) =>
              sum + value,
            0
          ) / ratings.length
        ).toFixed(1)
      : '—';

  const paginationHTML =
    totalPages > 1
      ? `
          <div
            class="performance-pagination"
            aria-label="صفحات سجل الإنجاز"
          >

            <button
              class="page-nav"
              type="button"
              data-action="prev"
              ${
                performanceCurrentPage === 1
                  ? 'disabled'
                  : ''
              }
            >
              السابق
            </button>

            ${
              Array.from(
                {
                  length: totalPages
                },
                (_, index) =>
                  index + 1
              )
                .map(
                  page => `
                    <button
                      class="page-number ${
                        page ===
                        performanceCurrentPage
                          ? 'active'
                          : ''
                      }"
                      type="button"
                      data-page="${page}"
                      aria-current="${
                        page ===
                        performanceCurrentPage
                          ? 'page'
                          : 'false'
                      }"
                    >
                      ${page}
                    </button>
                  `
                )
                .join('')
            }

            <button
              class="page-nav"
              type="button"
              data-action="next"
              ${
                performanceCurrentPage ===
                totalPages
                  ? 'disabled'
                  : ''
              }
            >
              التالي
            </button>

          </div>
        `
      : '';

  app.innerHTML = `

   <header class="page-head performance-page-head">

  <div>

    <h1>
      سجل الإنجاز
    </h1>

 <p>
  ${escapeHTML(CURRENT_SUPPORT)}
  — أدائي وأداء المنصة
</p>
  </div>

</header>


    <section
      class="performance-grid"
      aria-label="مؤشرات الإنجاز"
    >

      ${statCard(
        'tickets',
        owned.length,
        'الطلبات المسندة إليّ'
      )}

      ${statCard(
        'check',
        closed.length,
        'الطلبات المغلقة',
        false,
        'closed'
      )}

      ${statCard(
        'star',
        `
          <bdi dir="ltr">
            ${average}
            ${
              average !== '—'
                ? ' / 5'
                : ''
            }
          </bdi>
        `,
        'متوسط التقييم',
        false,
        'rating'
      )}

    </section>

${renderPlatformCharts(
  state.tickets
)}
    <section
      class="
        surface
        requests-surface
        performance-history
      "
    >

      <div class="surface-header">

        <h2>
          الطلبات المنجزة
        </h2>

      </div>


      <div class="table-wrap">

        <table class="data-table">

          <thead>

            <tr>
              <th>الطلب</th>
              <th>تاريخ الإنشاء</th>
              <th>التقييم</th>
              <th>الإجراء</th>
            </tr>

          </thead>


          <tbody>

            ${
              closed.length

                ? pageClosed
                    .map(
                      ticket => `

                        <tr>

                          <td
                            class="request-title"
                            data-label="الطلب"
                          >

                            <strong>
                              ${escapeHTML(
                                ticket.title
                              )}
                            </strong>

                            <small>
                              ${escapeHTML(
                                ticket.id
                              )}
                            </small>

                          </td>


                          <td
                            data-label="تاريخ الإنشاء"
                          >

                            ${escapeHTML(
                              formatDateTime(
                                ticket.createdAt
                                || ''
                              )
                            )}

                          </td>


                          <td
                            data-label="التقييم"
                          >

                            ${
                              ticket.rating

                                ? `
                                    <button
    class="rating-summary"
    type="button"
    data-rating-ticket="${ticket.id}"
    aria-expanded="false"
    aria-controls="rating-comment-${ticket.id}"
    title="عرض تعليق التقييم">

                                      <span>
                                        ${
                                          ticket
                                            .rating
                                            .value
                                        }
                                      </span>

                                      <span
                                        class="
                                          rating-star
                                        "
                                        aria-hidden="
                                          true
                                        "
                                      >
                                        ★
                                      </span>

                                    </button>
                                  `

                                : 'لم يُقيّم'
                            }

                          </td>


                          <td
                            class="row-actions-cell"
                          >

                            <div class="row-actions">

                              <button
                                class="button secondary small"
                                type="button"
                                data-view="${
                                  ticket.id
                                }"
                              >
                                عرض الطلب
                              </button>

                            </div>

                          </td>

                        </tr>


                        ${
                          ticket.rating

                            ? `
                                <tr
                                  class="
                                    rating-comment-row
                                  "
                                  id="rating-comment-${ticket.id}"

                                  hidden
                                >

                                  <td
                                    colspan="4"
                                  >

                                    <div
                                      class="
                                        rating-comment-box
                                      "
                                    >

                                      <strong>

                                        صاحب التقييم:

                                        ${escapeHTML(
                                          ticket
                                            .rating
                                            .rated_by
                                          || ticket
                                            .requester
                                          || ''
                                        )}

                                      </strong>


                                      <p>

                                        ${
                                          ticket
                                            .rating
                                            .comment

                                            ? escapeHTML(
                                                ticket
                                                  .rating
                                                  .comment
                                              )

                                            : `
                                                لم يكتب
                                                الموظف
                                                تعليقًا
                                              `
                                        }

                                      </p>

                                    </div>

                                  </td>

                                </tr>
                              `

                            : ''
                        }

                      `
                    )
                    .join('')

                : `
                    <tr>

                      <td colspan="4">

                        <div
                          class="empty-state"
                        >
                          لا توجد طلبات مغلقة
                          حتى الآن
                        </div>

                      </td>

                    </tr>
                  `
            }

          </tbody>

        </table>

      </div>

      ${paginationHTML}

    </section>
  `;


  app
    .querySelectorAll(
      '[data-view]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => navigate(
            'detail',
            button.dataset.view
          )
        );

      }
    );


  app
    .querySelectorAll(
      '[data-rating-ticket]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            const row =
              document.getElementById(
                `rating-comment-${
                  button.dataset
                    .ratingTicket
                }`
              );

            if (!row) {
              return;
            }

            const willOpen =
              row.hidden;

            app
              .querySelectorAll(
                '.rating-comment-row'
              )
              .forEach(
                item => {
                  item.hidden = true;
                }
              );

            app
              .querySelectorAll(
                '[data-rating-ticket]'
              )
              .forEach(
                item => {

                  item.setAttribute(
                    'aria-expanded',
                    'false'
                  );

                }
              );

            row.hidden =
              !willOpen;

            button.setAttribute(
              'aria-expanded',
              String(willOpen)
            );

          }
        );

      }
    );


  app
    .querySelectorAll(
      '.performance-pagination [data-page]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            performanceCurrentPage =
              Number(
                button.dataset.page
              );

            renderPerformance();

          }
        );

      }
    );


  const prevButton =
    app.querySelector(
      `
        .performance-pagination
        [data-action="prev"]
      `
    );

  const nextButton =
    app.querySelector(
      `
        .performance-pagination
        [data-action="next"]
      `
    );


  if (prevButton) {

    prevButton.addEventListener(
      'click',
      () => {

        if (
          performanceCurrentPage > 1
        ) {

          performanceCurrentPage -= 1;

          renderPerformance();

        }

      }
    );

  }


  if (nextButton) {

    nextButton.addEventListener(
      'click',
      () => {

        if (
          performanceCurrentPage <
          totalPages
        ) {

          performanceCurrentPage += 1;

          renderPerformance();

        }

      }
    );

  }
}
/*
 * Browser History
 */
if (isManagerPage) {

  /* يحصر تنسيقات المنصة في صفحاتها ولا يمسّ بقية موقع Odoo */
  document.body.classList.add('iu-portal');

  window.addEventListener(
    'hashchange',
    () => {

      const nextRoute =
        readRoute(
          'dashboard'
        );

      currentRoute =
        nextRoute.route;

      selectedTicketId =
        nextRoute.ticketId;

      render();
    }
  );

  render();
}