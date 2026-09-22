/** @odoo-module **/

import { registry } from "@web/core/registry";

const app =
  document.getElementById('app');

const isEmployeePage =
  app?.dataset.userName !== undefined;

/*
 * هوية الهيدر.
 * مسار الشعار يُقرأ من data-brand-logo على عنصر #app في قالب QWeb،
 * مثال: <div id="app" data-brand-logo="/<module>/static/src/img/logo.svg" ...>
 * وإن لم يوجد، يظهر اسم المنصة نصًا دون صورة مكسورة.
 */
const BRAND_NAME =
  app?.dataset.brandName ||
  'معهد البحوث والدراسات الاستشارية';

const BRAND_LOGO =
  app?.dataset.brandLogo || '';

const PORTAL_NAME =
  app?.dataset.portalName ||
  'منصة الدعم الفني';
/*
   Icons
    */

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

    if (!isEmployeePage) {
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
  'employee_support_chat_bus_service',
  supportChatBusService
);

function icon(name, label = '') {
  const aria =
    label
      ? `role="img" aria-label="${escapeHTML(label)}"`
      : 'aria-hidden="true"';

  return `
    <span
      class="icon"
      ${aria}
    >
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


/*
   General helpers
    */

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
/*
   Date and Time
    */

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


function getTicket(state, id) {
  return state.tickets.find(
    ticket =>
      String(ticket.id) ===
      String(id)
  );
}

function readRoute(defaultRoute) {
  const [
    route,
    ticketId = null
  ] =
    location.hash
      .replace(/^#/, '')
      .split('/');

  return {
    route:
      route || defaultRoute,

    ticketId
  };
}


function nowArabic() {
  return new Intl.DateTimeFormat(
    'ar-SA',
    {
      day: 'numeric',
      month: 'long',
      hour: 'numeric',
      minute: '2-digit'
    }
  ).format(
    new Date()
  );
}


/* =========================================================
   Badges
   ========================================================= */

function statusBadge(status) {
  const classes = {
    'جديد':
      'status-new',

    'قيد المعالجة':
      'status-processing',

    'بانتظار تأكيد الموظف':
      'status-confirmation',

    'بانتظار التقييم':
      'status-confirmation',

    'مغلق':
      'status-closed',

    'مسودة':
      'status-draft'
  };

  return `
    <span
      class="status ${classes[status] ||
    'status-new'
    }"
    >
      ${escapeHTML(status)}
    </span>
  `;
}


function priorityBadge(priority) {
  const classes = {
    'عالية':
      'priority-high',

    'متوسطة':
      'priority-medium',

    'منخفضة':
      'priority-low'
  };

  return `
    <span
      class="priority ${classes[priority] ||
    'priority-medium'
    }"
    >
      ${escapeHTML(priority)}
    </span>
  `;
}


/*
   Ticket progress
    */

const ticketStages = [
  {
    key: 'new',
    label: 'جديد'
  },

  {
    key: 'processing',
    label: 'قيد المعالجة'
  },

  {
    key: 'confirmation',
    label: 'بانتظار تأكيد الموظف'
  },

  {
    key: 'closed',
    label: 'مغلق'
  }
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

        ${statusBadge(ticket.status)}

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
    ticketStageIndex(
      ticket.status
    );

  return `
    <nav
      class="ticket-progress"
      aria-label="مراحل الطلب"
    >

      ${ticketStages
      .map(
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
              : `
                  <span>
                    ${index + 1}
                  </span>
                `;

          return `
              <div
                class="ticket-stage ${stateClass}"

                ${index === activeIndex
              ? 'aria-current="step"'
              : ''
            }
              >

                <span
                  class="ticket-stage-marker"
                >
                  ${marker}
                </span>

                <span
                  class="ticket-stage-label"
                >
                  ${stage.label}
                </span>

              </div>
            `;
        }
      )
      .join('')}

    </nav>
  `;
}


/*
   Stats
    */

function statCard(
  iconName,
  number,
  label,
  featured = false,
  tone = 'total'
) {
  return `
    <article
      class="stat-card ${featured
      ? 'featured'
      : ''
    }"
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


/*
   Attachment
    */

function renderAttachment(ticket) {
  if (!ticket.attachment) {
    return '';
  }

  return `
    <a
      class="attachment"
      href="/support/attachment/${ticket.attachment.id}"
      target="_blank"
      rel="noopener"
    >

      <span class="file-icon">
        ${icon('paperclip')}
      </span>

      <span class="attachment-info">

        <strong title="${escapeHTML(
    ticket.attachment.name || ''
  )}">
          ${escapeHTML(
    ticket.attachment.name || ''
  )}
        </strong>

        <small>
          فتح المرفق
        </small>

      </span>

    </a>
  `;
}


/*
   Chat
    */

function renderChat(
  ticket,
  currentRole,
  canSend = true
) {
  const messages =
    ticket.messages || [];

  return `
    <section
      class="surface chat-card"
    >

      <div class="surface-header">

        <h2>
          المحادثة داخل الطلب
        </h2>

      </div>

      <div
        class="chat-body"
        id="chat-body"
      >

        ${messages.length
      ? messages
        .map(
          message => `
                    <article
                      class="chat-message ${message.sender ===
              currentRole
              ? 'mine'
              : 'theirs'
            }"
                    >

                      <strong class="chat-author">
  ${escapeHTML(
              message.name || ''
            )}
</strong>

${message.text
              ? `
      <p class="chat-text">
        ${escapeHTML(
                message.text
              )}
      </p>
    `
              : ''
            }

${(message.attachments || []).length
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
        )
        .join('')

      : `
              <div class="chat-empty">
                لا توجد رسائل حتى الآن
              </div>
            `
    }

      </div>

      ${canSend
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

async function loadTicketMessages(ticket) {
  try {
    const response = await fetch(
      `/support/ticket/messages?ticket_number=${encodeURIComponent(ticket.id)}`
    );

    const result =
      await response.json();

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

    ticket.messages =
      (result.messages || []).map(
        message => ({
          id:
            message.id,

          sender:
            message.mine
              ? 'employee'
              : 'support',

          name:
            message.author || '',

          text:
            message.text || '',
          time:
            formatDateTime(
              message.created_at
            ),

          attachments:
            message.attachments || []
        })
      );

    return true;

  } catch (error) {
    console.error(
      'Load chat error:',
      error
    );

    return false;
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
          'Send chat error:',
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
   Timeline
    */

function renderTimeline(
  items = []
) {
  return `
    <ol class="timeline">

      ${items
      .map(
        item => `
            <li>

              <strong>
                ${escapeHTML(
          item.title || ''
        )}
              </strong>

              <small>
                ${escapeHTML(
          formatDateTime(
            item.meta
          ))}
              </small>

            </li>
          `
      )
      .join('')}

    </ol>
  `;
}

/*
   Toast
    */


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
    <span class="toast-state-icon" aria-hidden="true"></span>
    <span class="toast-message"></span>
    <span class="toast-progress" aria-hidden="true"></span>
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

/*
   Navigation shell
    */

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
    document.getElementById(
      'topbar'
    );

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

        ${BRAND_LOGO
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

        ${items
      .map(
        item => `
              <a
                href="#${item.key}"
                class="nav-link ${active === item.key
            ? 'active'
            : ''
          }"
                data-route="${item.key}"
                ${active === item.key
            ? 'aria-current="page"'
            : ''
          }
              >

                <span>
                  ${item.label}
                </span>

              </a>
            `
      )
      .join('')}

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



  /* لو كان مسار الشعار خاطئًا نحذف الصورة بدل إظهار أيقونة مكسورة */
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
async function loadEmployeeNotifications() {
  try {
    const response = await fetch(
      '/support/notifications'
    );

    const result = await response.json();

    if (
      !response.ok ||
      !result.success
    ) {
      console.error(
        'Notifications error:',
        result.message
      );

      return false;
    }

    state.notifications.employee =
      (
        result.notifications || []
      ).map(
        notification => ({
          id: String(
            notification.id
          ),

          title:
            notification.title ||
            'تحديث على طلب الدعم',

          text:
            notification.message ||
            '',

          time:
            formatDateTime(
              notification.created_at
            ),

          read:
            Boolean(
              notification.is_read
            ),

          ticketId:
            notification.ticket_number ||
            ''
        })
      );

    return true;

  } catch (error) {
    console.error(
      'Load employee notifications error:',
      error
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
      state.notifications?.[role] ||
      [];

    const unread =
      items.filter(
        item => !item.read
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

        ${unread
        ? `
              <button
                class="text-button"
                id="mark-read"
                type="button"
              >
                تحديد الكل كمقروء
              </button>
            `
        : ''
      }

      </div>

      <div class="notification-list">

        ${items.length
        ? items.map(
          item => `
                  <button
                    type="button"
                    class="notification-item ${item.read
              ? ''
              : 'unread'
            }"
                    data-notification="${item.id
            }"
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
        ).join('')

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

          items.forEach(
            item => {
              item.read = true;
            }
          );

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
          itemButton.addEventListener(
            'click',
            async () => {
              const item =
                items.find(
                  entry =>
                    String(
                      entry.id
                    ) ===
                    itemButton
                      .dataset
                      .notification
                );

              if (!item) {
                return;
              }

              const success =
                await markNotificationRead(
                  item.id
                );

              if (!success) {
                showToast(
                  'تعذر تحديث الإشعار'
                );

                return;
              }

              item.read = true;

              draw();

              panel.hidden = true;

              button.setAttribute(
                'aria-expanded',
                'false'
              );

              if (item.ticketId) {
                openTicket(
                  item.ticketId
                );
              }
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

          if (currentPanel) {
            currentPanel.hidden =
              true;
          }
        }
      }
    );
  }
}

/*
   Employee state
    */

const state = {
  tickets: [],

  notifications: {
    employee: [],
    support: []
  }
};

const CURRENT_EMPLOYEE =
  app?.dataset.userName ||
  'الموظف';

const CURRENT_DEPARTMENT =
  app?.dataset.department ||
  'المالية';

const initialRoute =
  readRoute(
    'requests'
  );


let currentRoute =
  initialRoute.route;


let selectedTicketId =
  initialRoute.ticketId;

let employeeRequestsPage = 1;

const EMPLOYEE_PAGE_SIZE = 10;
let detailReturnRoute =
  'requests';

/*
   Navigation
 */

function navigate(
  route,
  ticketId = null
) {
  if (
    route === 'detail' &&
    (
      currentRoute === 'requests' ||
      currentRoute === 'all-requests'
    )
  ) {
    detailReturnRoute =
      currentRoute;
  }
  currentRoute =
    route;

  selectedTicketId =
    ticketId;


  history.replaceState(
    null,
    '',
    `#${route}${ticketId
      ? `/${ticketId}`
      : ''
    }`
  );


  render();
}


/*
   Main render
    */
async function render() {
  await loadEmployeeNotifications();

  const routeKey =
    [
      'detail',
      'all-requests'
    ].includes(currentRoute)
      ? 'requests'
      : currentRoute;

  mountShell({
    role: 'employee',
    active: routeKey,
    navigate
  });

  bindNotifications(
    state,
    'employee',
    id =>
      navigate(
        'detail',
        id
      )
  );

  if (
    currentRoute === 'new'
  ) {

    renderNewRequest();

  } else if (
    currentRoute === 'detail'
  ) {

    await renderDetail(
      selectedTicketId
    );

  } else if (
    currentRoute ===
    'all-requests'
  ) {

    await renderAllRequests();

  } else {

    await renderRequests();

  }
}

/*
   Load employee tickets from Odoo
    */

async function renderRequests() {
  try {
    const response =
      await fetch(
        '/support/tickets'
      );

    const result =
      await response.json();


    if (
      !response.ok ||
      !result.success
    ) {
      showToast(
        'تعذر تحميل الطلبات'
      );

      return;
    }

    const allTickets =
      result.tickets || [];

    const tickets =
      allTickets.filter(
        ticket =>
          ticket.status !==
          'مسودة'
      );

    state.tickets =
      tickets;


    /*
     * آخر 3 طلبات
     */
    const latestTickets =
      [...tickets]
        .sort(
          (a, b) =>
            new Date(
              b.createdAt
            ) -
            new Date(
              a.createdAt
            )
        )
        .slice(
          0,
          3
        );


    app.innerHTML = `
<header
  class="
    page-head
    requests-page-head
  "
>
  <div>
    <h1>
      الرئيسية
    </h1>

    <p>
      نظرة شاملة على طلبات الدعم المقدمة
    </p>
  </div>
</header>
      <section
        class="
          stats-grid
          requests-stats
        "
        aria-label="
          ملخص الطلبات
        "
      >

        ${statCard(
      'tickets',

      tickets.length,

      'جميع الطلبات',

      false,

      'total'
    )}


        ${statCard(
      'inbox',

      tickets.filter(
        ticket =>
          ticket.status ===
          'جديد'
      ).length,

      'الطلبات الجديدة',

      false,

      'new'
    )}


        ${statCard(
      'clock',

      tickets.filter(
        ticket =>
          ticket.status ===
          'قيد المعالجة'
      ).length,

      'قيد المعالجة',

      false,

      'processing'
    )}


        ${statCard(
      'check',

      tickets.filter(
        ticket =>
          ticket.status ===
          'مغلق'
      ).length,

      'الطلبات المغلقة',

      false,

      'closed'
    )}

      </section>


      <section
        class="
          surface
          requests-surface
        "
      >

        <div
          class="surface-header"
        >

          <h2>
آخر الطلبات
       </h2>

        </div>


        <div
          class="
            table-wrap
            requests-table-wrap
          "
        >

          <table
            class="
              data-table
              requests-table
            "
          >

            <colgroup>

              <col class="col-number">

              <col class="col-request">

              <col class="col-type">

              <col class="col-status">

              <col class="col-assignee">

              <col class="col-date">

              <col class="col-action">

            </colgroup>


            <thead>

              <tr>

                <th>
                  رقم الطلب
                </th>

                <th>
                  موضوع الطلب
                </th>

                <th>
                  النوع
                </th>

                <th>
                  الحالة
                </th>

                <th>
                  مسؤول الدعم
                </th>

                <th>
                  تاريخ الإنشاء
                </th>

                <th>
                  الإجراء
                </th>

              </tr>

            </thead>


            <tbody
              id="latest-employee-rows"
            >
            </tbody>

          </table>

        </div>


        <div
          class="requests-view-all"
        >

          <button
  class="view-all-link"
  type="button"
  id="view-all-requests"
>
  عرض جميع الطلبات
</button>

        </div>

      </section>
    `;


    drawLatestEmployeeRows(
      latestTickets
    );


    document
      .getElementById(
        'view-all-requests'
      )
      ?.addEventListener(
        'click',
        () => {

          employeeRequestsPage =
            1;

          navigate(
            'all-requests'
          );

        }
      );


  } catch (error) {

    console.error(
      'Employee tickets error:',
      error
    );

    showToast(
      'حدث خطأ أثناء تحميل الطلبات'
    );
  }
}
function drawLatestEmployeeRows(
  tickets
) {
  const rows =
    document.getElementById(
      'latest-employee-rows'
    );

  if (!rows) {
    return;
  }


  rows.innerHTML =
    tickets.length

      ? tickets
        .map(
          ticket => `
              <tr>

                <td
                  data-label="
                    رقم الطلب
                  "
                >

                  <span
                    class="
                      request-code
                    "
                  >
                    ${escapeHTML(
            ticket.id
          )}
                  </span>

                </td>


                <td
                  class="
                    request-title
                  "
                  data-label="
                    موضوع الطلب
                  "
                >

                  <strong>
                    ${escapeHTML(
            ticket.title
          )}
                  </strong>

                </td>


                <td
                  data-label="النوع"
                >
                  ${escapeHTML(
            ticket.type ||
            '—'
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
                  data-label="
                    مسؤول الدعم
                  "
                >

                  ${escapeHTML(
            ticket.assignee ||
            'بانتظار الاستلام'
          )}

                </td>


                <td
                  data-label="
                    تاريخ الإنشاء
                  "
                >

                  ${escapeHTML(
            formatDateTime(
              ticket.createdAt
            )
          )}

                </td>


                <td
                  class="
                    row-actions-cell
                  "
                >

                  <div
                    class="row-actions"
                  >

                    <button
                      class="
                        button
                        secondary
                        small
                      "
                      type="button"
                      data-view="${ticket.id
            }"
                    >
                      عرض الطلب
                    </button>

                  </div>

                </td>

              </tr>
            `
        )
        .join('')

      : `
          <tr>

            <td colspan="7">

              <div
                class="empty-state"
              >
                لا توجد طلبات
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
          () => {

            navigate(
              'detail',
              button.dataset.view
            );

          }
        );

      }
    );
}

async function renderAllRequests() {
  try {
    const response =
      await fetch(
        '/support/tickets'
      );

    const result =
      await response.json();

    if (
      !response.ok ||
      !result.success
    ) {
      showToast(
        'تعذر تحميل الطلبات'
      );

      return;
    }

    const allTickets =
      result.tickets || [];

    const drafts =
      allTickets.filter(
        ticket =>
          ticket.status ===
          'مسودة'
      );

    const tickets =
      allTickets.filter(
        ticket =>
          ticket.status !==
          'مسودة'
      );

    state.tickets =
      tickets;

    app.innerHTML = `

      <a
        class="page-back all-requests-back"
        href="#requests"
        id="back-to-home"
      >
        ${icon('arrow')}
العودة إلى الرئيسية
        </a>

      <header
        class="
          page-head
          requests-page-head
        "
      >
        <div>
          <h1>
            جميع الطلبات
          </h1>
        </div>
      </header>


      <section
        class="
          surface
          requests-surface
        "
      >

        <div
          class="surface-header"
        >

          <h2>
            الطلبات
          </h2>


          <div
            class="
              filter-control
              search-box
            "
          >

            ${icon('search')}

            <input
              class="
                field-control
                search-control
              "
              id="employee-search"
              type="search"
              placeholder="ابحث برقم الطلب أو العنوان"
              aria-label="البحث في الطلبات"
            >

          </div>


          <div
            class="
              filter-control
              status-filter-box
            "
          >

            <select
              class="field-control"
              id="employee-status"
              aria-label="تصفية حسب الحالة"
            >
              <option>كل الحالات</option>
              <option>مسودة</option>
              <option>جديد</option>
              <option>قيد المعالجة</option>
              <option>بانتظار تأكيد الموظف</option>
              <option>مغلق</option>
            </select>

          </div>

        </div>


        <div
          class="
            table-wrap
            requests-table-wrap
          "
        >

          <table
            class="
              data-table
              requests-table
            "
          >

            <colgroup>

              <col class="col-number">
              <col class="col-request">
              <col class="col-type">
              <col class="col-status">
              <col class="col-assignee">
              <col class="col-date">
              <col class="col-action">

            </colgroup>


            <thead>

              <tr>

                <th>
                  رقم الطلب
                </th>

                <th>
                  موضوع الطلب
                </th>

                <th>
                  النوع
                </th>

                <th>
                  الحالة
                </th>

                <th>
                  مسؤول الدعم
                </th>

                <th>
                  تاريخ الإنشاء
                </th>

                <th>
                  الإجراء
                </th>

              </tr>

            </thead>


            <tbody
              id="employee-rows"
            >
            </tbody>

          </table>

        </div>


        <div
          class="requests-pagination"
          id="employee-pagination"
        >
        </div>

      </section>
    `;


    document
      .getElementById(
        'back-to-home'
      )
      ?.addEventListener(
        'click',
        event => {

          event.preventDefault();

          navigate(
            'requests'
          );

        }
      );


    document
      .getElementById(
        'employee-search'
      )
      ?.addEventListener(
        'input',
        () => {

          employeeRequestsPage =
            1;

          drawEmployeeRows(
            tickets,
            drafts
          );

        }
      );


    document
      .getElementById(
        'employee-status'
      )
      ?.addEventListener(
        'change',
        () => {

          employeeRequestsPage =
            1;

          drawEmployeeRows(
            tickets,
            drafts
          );

        }
      );


    drawEmployeeRows(
      tickets,
      drafts
    );

  } catch (error) {

    console.error(
      'All employee tickets error:',
      error
    );

    showToast(
      'حدث خطأ أثناء تحميل الطلبات'
    );
  }
}
/*
   Draw employee requests
    */

function drawEmployeeRows(
  tickets,
  drafts
) {
  const searchInput =
    document.getElementById(
      'employee-search'
    );

  const statusFilter =
    document.getElementById(
      'employee-status'
    );

  const rows =
    document.getElementById(
      'employee-rows'
    );

  const pagination =
    document.getElementById(
      'employee-pagination'
    );

  if (
    !searchInput ||
    !statusFilter ||
    !rows ||
    !pagination
  ) {
    return;
  }


  const query =
    searchInput.value
      .trim()
      .toLowerCase();


  const filter =
    statusFilter.value;


  /*
   * الطلبات العادية
   */
  const visibleTickets =
    tickets.filter(
      ticket => {

        const matchesText =
          `
            ${ticket.id || ''}
            ${ticket.title || ''}
          `
            .toLowerCase()
            .includes(query);


        const matchesStatus =
          filter ===
          'كل الحالات' ||

          ticket.status ===
          filter;


        return (
          matchesText &&
          matchesStatus
        );
      }
    );


  /*
   * المسودات
   */
  const visibleDrafts =
    drafts.filter(
      draft => {

        const matchesText =
          `
            ${draft.id || ''}
            ${draft.title || ''}
            ${draft.type || ''}
          `
            .toLowerCase()
            .includes(query);


        const matchesStatus =
          filter ===
          'كل الحالات' ||

          filter ===
          'مسودة';


        return (
          matchesText &&
          matchesStatus
        );
      }
    );


  /*
   * نجمع الكل في مصفوفة واحدة
   */
  const allVisible = [

    ...visibleDrafts.map(
      draft => ({
        kind: 'draft',

        data: draft,

        date:
          draft.savedAt ||
          draft.createdAt ||
          ''
      })
    ),

    ...visibleTickets.map(
      ticket => ({
        kind: 'ticket',

        data: ticket,

        date:
          ticket.createdAt ||
          ''
      })
    )

  ];


  /*
   * الأحدث أولاً
   */
  allVisible.sort(
    (a, b) =>
      new Date(
        b.date || 0
      ) -
      new Date(
        a.date || 0
      )
  );


  /*
   * عدد الصفحات
   */
  const totalPages =
    Math.max(
      1,

      Math.ceil(
        allVisible.length /
        EMPLOYEE_PAGE_SIZE
      )
    );


  if (
    employeeRequestsPage >
    totalPages
  ) {
    employeeRequestsPage =
      totalPages;
  }


  /*
   * أول وآخر سجل في الصفحة
   */
  const startIndex =
    (
      employeeRequestsPage - 1
    ) *
    EMPLOYEE_PAGE_SIZE;


  const pageItems =
    allVisible.slice(
      startIndex,
      startIndex +
      EMPLOYEE_PAGE_SIZE
    );


  /*
   * رسم الجدول
   */
  rows.innerHTML =
    pageItems.length

      ? pageItems
        .map(
          record => {

            /*
             * المسودة
             */
            if (
              record.kind ===
              'draft'
            ) {
              const draft =
                record.data;

              return `
                  <tr>

                    <td
                      data-label="رقم الطلب"
                    >

                      <span
                        class="draft-code"
                      >
                        ${escapeHTML(
                draft.id ||
                'مسودة'
              )}
                      </span>

                    </td>


                    <td
                      class="
                        request-title
                        draft-title
                      "
                      data-label="
                        موضوع الطلب
                      "
                    >

                      <span>

                        <strong>
                          ${escapeHTML(
                draft.title ||
                'مسودة بدون عنوان'
              )}
                        </strong>

                        <small>
                          ${escapeHTML(
                draft.department ||
                CURRENT_DEPARTMENT
              )}
                        </small>

                      </span>

                    </td>


                    <td
                      data-label="النوع"
                    >
                      ${escapeHTML(
                draft.type ||
                '—'
              )}
                    </td>


                    <td
                      data-label="الحالة"
                    >
                      ${statusBadge(
                'مسودة'
              )}
                    </td>


                    <td
                      data-label="
                        مسؤول الدعم
                      "
                    >
                      —
                    </td>


                    <td
                      data-label="
                        تاريخ الحفظ
                      "
                    >
                      ${escapeHTML(
                formatDateTime(
                  draft.savedAt
                )
              )}
                    </td>


                    <td
                      class="
                        row-actions-cell
                      "
                    >

                      <div
                        class="
                          row-actions
                        "
                      >

                        <button
                          class="
                            button
                            secondary
                            small
                          "
                          type="button"

                          data-edit-draft="${draft.draft_id
                }"
                        >
                          تعديل
                        </button>


                        <button
                          class="
                            button
                            small
                          "
                          type="button"

                          data-send-draft="${draft.draft_id
                }"
                        >
                          إرسال
                        </button>


                        <button
                          class="
                            button
                            secondary
                            small
                            danger-text
                          "
                          type="button"

                          data-delete-draft="${draft.draft_id
                }"
                        >
                          حذف
                        </button>

                      </div>

                    </td>

                  </tr>
                `;
            }


            /*
             * الطلب العادي
             */
            const ticket =
              record.data;

            return `
                <tr>

                  <td
                    data-label="
                      رقم الطلب
                    "
                  >

                    <span
                      class="
                        request-code
                      "
                    >
                      ${escapeHTML(
              ticket.id
            )}
                    </span>

                  </td>


                  <td
                    class="
                      request-title
                    "
                    data-label="
                      موضوع الطلب
                    "
                  >

                    <strong>
                      ${escapeHTML(
              ticket.title
            )}
                    </strong>

                  </td>


                  <td
                    data-label="النوع"
                  >
                    ${escapeHTML(
              ticket.type ||
              '—'
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
                    data-label="
                      مسؤول الدعم
                    "
                  >
                    ${escapeHTML(
              ticket.assignee ||
              'بانتظار الاستلام'
            )}
                  </td>


                  <td
                    data-label="
                      تاريخ الإنشاء
                    "
                  >
                    ${escapeHTML(
              formatDateTime(
                ticket.createdAt
              )
            )}
                  </td>


                  <td
                    class="
                      row-actions-cell
                    "
                  >

                    <div
                      class="
                        row-actions
                      "
                    >

                      <button
                        class="
                          button
                          secondary
                          small
                        "
                        type="button"

                        data-view="${ticket.id
              }"
                      >
                        عرض الطلب
                      </button>


                      ${ticket.status ===
                'مغلق' &&
                !ticket.rating

                ? `
                              <button
                                class="
                                  button
                                  gold
                                  small
                                "
                                type="button"

                                data-rate="${ticket.id
                }"
                              >
                                تقييم الخدمة
                              </button>
                            `

                : ''
              }

                    </div>

                  </td>

                </tr>
              `;
          }
        )
        .join('')

      : `
          <tr>

            <td colspan="7">

              <div
                class="empty-state"
              >

                ${icon('inbox')}

                <div>
                  لا توجد طلبات مطابقة
                </div>

              </div>

            </td>

          </tr>
        `;


  /*
   * Pagination
   */
  pagination.innerHTML =
    allVisible.length >
      EMPLOYEE_PAGE_SIZE

      ? `
          <div
            class="
              requests-pagination-inner
            "
          >

            <button
              type="button"
              data-page-action="prev"

              ${employeeRequestsPage === 1
        ? 'disabled'
        : ''
      }
            >
              السابق
            </button>


            ${Array.from(
        {
          length:
            totalPages
        },

        (_, index) =>
          index + 1
      )
        .map(
          page => `
                  <button
                    type="button"

                    class="${page ===
              employeeRequestsPage
              ? 'active'
              : ''
            }"

                    data-page="${page
            }"

                    ${page ===
              employeeRequestsPage
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

              ${employeeRequestsPage ===
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


  /*
   * عرض الطلب
   */
  rows
    .querySelectorAll(
      '[data-view]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            navigate(
              'detail',
              button.dataset.view
            );

          }
        );

      }
    );


  /*
   * تقييم
   */
  rows
    .querySelectorAll(
      '[data-rate]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            navigate(
              'detail',
              button.dataset.rate
            );

          }
        );

      }
    );


  /*
   * تعديل المسودة
   */
  rows
    .querySelectorAll(
      '[data-edit-draft]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            navigate(
              'new',
              button.dataset
                .editDraft
            );

          }
        );

      }
    );


  /*
   * إرسال المسودة
   */
  rows
    .querySelectorAll(
      '[data-send-draft]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            sendDraft(
              Number(
                button.dataset
                  .sendDraft
              )
            );

          }
        );

      }
    );


  /*
   * حذف المسودة
   */
  rows
    .querySelectorAll(
      '[data-delete-draft]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            deleteDraft(
              Number(
                button.dataset
                  .deleteDraft
              )
            );

          }
        );

      }
    );


  /*
   * أرقام الصفحات
   */
  pagination
    .querySelectorAll(
      '[data-page]'
    )
    .forEach(
      button => {

        button.addEventListener(
          'click',
          () => {

            employeeRequestsPage =
              Number(
                button.dataset.page
              );

            drawEmployeeRows(
              tickets,
              drafts
            );

          }
        );

      }
    );


  /*
   * السابق / التالي
   */
  pagination
    .querySelector(
      '[data-page-action="prev"]'
    )
    ?.addEventListener(
      'click',
      () => {

        if (
          employeeRequestsPage >
          1
        ) {
          employeeRequestsPage -=
            1;

          drawEmployeeRows(
            tickets,
            drafts
          );
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
          employeeRequestsPage <
          totalPages
        ) {
          employeeRequestsPage +=
            1;

          drawEmployeeRows(
            tickets,
            drafts
          );
        }

      }
    );
}
/*
   New support request
    */

async function renderNewRequest() {
  let draft = null;

  const draftId =
    selectedTicketId !== null
      ? Number(selectedTicketId)
      : null;

  if (
    Number.isInteger(draftId)
  ) {
    try {
      const response = await fetch(
        `/support/draft/${draftId}`
      );

      const result =
        await response.json();

      if (
        response.ok &&
        result.success
      ) {
        draft = result.draft;
      } else {
        showToast(
          result.message ||
          'تعذر تحميل المسودة'
        );

        return navigate(
          'requests'
        );
      }

    } catch (error) {
      console.error(
        'Load draft error:',
        error
      );

      showToast(
        'حدث خطأ أثناء تحميل المسودة'
      );

      return navigate(
        'requests'
      );
    }
  }

  app.innerHTML = `
    <header
      class="page-head new-request-heading"
    >

      <h1>
        إنشاء طلب دعم فني
      </h1>

    </header>


    <form
      class="surface form-card"
      id="new-request-form"
    >

      <div class="surface-header">

        <div>

          <h2>
            بيانات الطلب
          </h2>

        </div>

      </div>

<div class="surface-body">

  <div class="form-grid">

    <div class="form-field">

      <label for="type">
        نوع الطلب
        <span class="required"></span>
      </label>

      <select
        class="field-control"
        id="type"
        required
      >
        <option value="">
          اختر النوع
        </option>

        <option>استفسار</option>
<option>مشكلة تقنية</option>
<option>طلب خدمة</option>
<option>جمع متطلبات</option>
      </select>

    </div>

    <div class="form-field">

      <label for="priority">
        الأولوية
        <span class="required"></span>
      </label>

      <select
        class="field-control"
        id="priority"
        required
      >
        <option value="">
          اختر الأولوية
        </option>

        <option>
          متوسطة
        </option>

        <option>
          عالية
        </option>

        <option>
          منخفضة
        </option>
      </select>

    </div>

    <div class="form-field full">

            <label
              for="subject"
            >
              موضوع الطلب

              <span class="required"></span>

            </label>


            <input
              class="field-control"
              id="subject"
              required
              minlength="5"
              maxlength="100"
              placeholder="اكتب موضوع الطلب "
              value="${escapeHTML(
    draft?.title ||
    ''
  )}"
            >

          </div>


          <div
            class="form-field full"
          >

            <label
              for="description"
            >
             تفاصيل الطلب

              <span class="required"></span>

            </label>


            <textarea
              class="field-control"
              id="description"
              required
              minlength="10"
              placeholder=" اكتب تفاصيل الطلب "
            >${escapeHTML(
    draft?.description ||
    ''
  )}</textarea>

          </div>


          <div
            class="form-field full"
          >

 <label for="attachment">
  المرفقات

  <span class="optional-label">
  (اختياري)
  </span>
</label>

<small class="hint">
  الحد الأقصى لحجم الملف 10 ميجابايت
</small>

            <label
              class="upload-control"
              for="attachment"
            >

              <span
                class="upload-button"
              >

                ${icon(
    'paperclip'
  )}

                اختيار ملف

              </span>


              <span
                class="upload-name"
                id="attachment-name"
              >
                لم يتم اختيار ملف
              </span>


              <input
                class="visually-hidden"
                id="attachment"
                type="file"
              >

            </label>

          </div>

        </div>


        <div
          class="form-actions"
        >

          <div
            class="form-actions-group"
          >

            <button
              class="button secondary"
              type="button"
              id="cancel-request"
            >
              إلغاء
            </button>


            <button
              class="button secondary"
              type="button"
              id="save-draft"
            >
              حفظ كمسودة
            </button>

          </div>


          <button
            class="button"
            type="submit"
          >

            ${icon(
    'send'
  )}

            إرسال الطلب

          </button>

        </div>

      </div>

    </form>
  `;
  if (draft) {
    document
      .getElementById('type')
      .value =
      draft.type || '';

    document
      .getElementById('priority')
      .value =
      draft.priority || '';
  }
  const typeField =
  document.getElementById(
    'type'
  );

const priorityField =
  document.getElementById(
    'priority'
  );

function updatePriorityOptions() {
  if (
    !typeField ||
    !priorityField
  ) {
    return;
  }

  const isInquiry =
    typeField.value ===
    'استفسار';

  priorityField.innerHTML = `
    <option value="">
      اختر الأولوية
    </option>

    <option value="medium">
      متوسطة
    </option>

    ${
      !isInquiry
        ? `
            <option value="high">
              عالية
            </option>
          `
        : ''
    }

    <option value="low">
      منخفضة
    </option>
  `;
}

if (draft) {
  typeField.value =
    draft.type || '';

  updatePriorityOptions();

  priorityField.value =
    draft.priority || '';
} else {
  updatePriorityOptions();
}

typeField?.addEventListener(
  'change',
  () => {
    updatePriorityOptions();

    priorityField.value = '';
  }
);

  document
    .getElementById(
      'cancel-request'
    )
    .addEventListener(
      'click',
      () =>
        navigate(
          'requests'
        )
    );


  document
    .getElementById(
      'save-draft'
    )
    .addEventListener(
      'click',
      saveDraft
    );


  const requestForm =
    document.getElementById(
      'new-request-form'
    );


  bindArabicValidation(
    requestForm
  );


  requestForm.addEventListener(
    'submit',
    submitRequest
  );

  const MAX_FILE_SIZE = 10 * 1024 * 1024;

  document
    .getElementById('attachment')
    .addEventListener('change', event => {
      const file = event.target.files[0];

      if (!file) {
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        showToast(
          'حجم الملف يجب ألا يتجاوز 10 ميجابايت',
          'warning'
        );
        event.target.value = '';

        document
          .getElementById('attachment-name')
          .textContent =
          'لم يتم اختيار ملف';

        return;
      }

      document
        .getElementById('attachment-name')
        .textContent =
        file.name;
    });
}

/*
   Validation
    */

function bindArabicValidation(form) {
  if (!form) return;

  const messages = {
    priority: {
      valueMissing: 'الرجاء اختيار الأولوية'
    },

    type: {
      valueMissing: 'الرجاء اختيار نوع الطلب'
    },

    subject: {
      valueMissing: 'الرجاء إدخال موضوع الطلب',
      tooShort: 'يجب ألا يقل موضوع الطلب عن 5 أحرف'
    },

    description: {
      valueMissing: 'الرجاء إدخال تفاصيل المشكلة',
      tooShort: 'يجب ألا يقل تفاصيل المشكلة عن 10 أحرف'
    }
  };

  form
    .querySelectorAll('[required], [minlength]')
    .forEach(field => {
      const applyMessage = () => {
        field.setCustomValidity('');

        const fieldMessages = messages[field.id];

        if (!fieldMessages) return;

        if (
          field.validity.valueMissing &&
          fieldMessages.valueMissing
        ) {
          field.setCustomValidity(
            fieldMessages.valueMissing
          );
        } else if (
          field.validity.tooShort &&
          fieldMessages.tooShort
        ) {
          field.setCustomValidity(
            fieldMessages.tooShort
          );
        }
      };

      // إنشاء رسالة أسفل الحقل.
      const errorText = document.createElement('small');

      errorText.className = 'field-error-message';
      errorText.id = `${field.id}-error`;
      errorText.hidden = true;

      field.insertAdjacentElement('afterend', errorText);

      // ربط الرسالة بالحقل مع الحفاظ على وصفه الموجود.
      const descriptions = new Set(
        (field.getAttribute('aria-describedby') || '')
          .split(/\s+/)
          .filter(Boolean)
      );

      descriptions.add(errorText.id);

      field.setAttribute(
        'aria-describedby',
        [...descriptions].join(' ')
      );

      const updateError = () => {
        applyMessage();

        const invalid = !field.validity.valid;

        field.classList.toggle('has-error', invalid);

        field.setAttribute(
          'aria-invalid',
          String(invalid)
        );

        errorText.textContent = invalid
          ? field.validationMessage
          : '';

        errorText.hidden = !invalid;
      };

      field.addEventListener('invalid', event => {
        // إخفاء نافذة المتصفح مع بقاء التحقق فعالًا.
        event.preventDefault();

        updateError();

        requestAnimationFrame(() => {
          const firstInvalid = form.querySelector(
            '.has-error[aria-invalid="true"]'
          );

          if (firstInvalid === field) {
            field.focus();
          }
        });
      });

      const handleEdit = () => {
        if (field.classList.contains('has-error')) {
          updateError();
        } else {
          applyMessage();
        }
      };

      field.addEventListener('input', handleEdit);
      field.addEventListener('change', handleEdit);
    });
}

/*
   Read request form*/

function readForm() {
  return {

    type:
      document
        .getElementById(
          'type'
        )
        .value,


    department:
      CURRENT_DEPARTMENT,


    priority:
      document
        .getElementById(
          'priority'
        )
        .value,


    title:
      document
        .getElementById(
          'subject'
        )
        .value
        .trim(),


    description:
      document
        .getElementById(
          'description'
        )
        .value
        .trim(),


    file:
      document
        .getElementById(
          'attachment'
        )
        .files[0]
  };
}


/*
   Draft
    */
async function saveDraft() {
  const data = readForm();

  if (
    !data.title &&
    !data.description &&
    !data.type &&
    !data.priority &&
    !data.file
  ) {
    showToast(
      'أدخل بعض بيانات الطلب قبل حفظ المسودة',
      'warning'
    );
    return;
  }

  const draftId =
    selectedTicketId !== null
      ? Number(selectedTicketId)
      : null;

  const formData =
    new FormData();

  if (draftId) {
    formData.append(
      'draft_id',
      draftId
    );
  }

  formData.append(
    'title',
    data.title
  );

  formData.append(
    'description',
    data.description
  );

  formData.append(
    'category',
    data.type
  );

  formData.append(
    'priority',
    data.priority
  );
  formData.append(
    'department',
    data.department
  );

  if (data.file) {
    formData.append(
      'attachment',
      data.file
    );
  }

  try {
    const response = await fetch(
      '/support/draft/save',
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
        'تعذر حفظ المسودة'
      );

      return;
    }

    showToast(
      result.message ||
      'تم حفظ المسودة بنجاح',
      'success'
    );

    setTimeout(() => {
      navigate('requests');
    }, 1000);

  } catch (error) {
    console.error(
      'Save draft error:',
      error
    );

    showToast(
      'حدث خطأ أثناء حفظ المسودة'
    );
  }
}


/*
   Send draft to Odoo
    */

async function sendDraft(draftId) {
  try {
    const response = await fetch(
      '/support/draft/submit',
      {
        method: 'POST',

        headers: {
          'Content-Type':
            'application/json'
        },

        body: JSON.stringify({
          draft_id: draftId
        })
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
        'تعذر إرسال المسودة'
      );

      return;
    }

    showToast(
      `تم إنشاء طلبك بنجاح - ${result.ticket_number}`,
      'success'
    );

    setTimeout(() => {
      navigate('requests');
    }, 1500);

  } catch (error) {
    console.error(
      'Send draft error:',
      error
    );

    showToast(
      'حدث خطأ أثناء إرسال المسودة'
    );
  }
}
/*
   delet draft to Odoo
    */
async function deleteDraft(draftId) {
  try {
    const response = await fetch(
      '/support/draft/delete',
      {
        method: 'POST',
        headers: {
          'Content-Type':
            'application/json'
        },
        body: JSON.stringify({
          draft_id: draftId
        })
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
        'تعذر حذف المسودة'
      );

      return;
    }

    showToast(
      result.message ||
      'تم حذف المسودة بنجاح',
      'success'
    );
    render();

  } catch (error) {
    console.error(
      'Delete draft error:',
      error
    );

    showToast(
      'حدث خطأ أثناء حذف المسودة'
    );
  }
}

/*
   Create  ticket
    */
async function submitRequest(event) {
  event.preventDefault();

  const submitButton =
    event.submitter ||
    event.currentTarget.querySelector(
      'button[type="submit"]'
    );

  if (submitButton?.disabled) {
    return;
  }

  if (submitButton) {
    submitButton.disabled = true;
  }

  const data = readForm();

  const draftId =
    selectedTicketId !== null
      ? Number(selectedTicketId)
      : null;

  try {
    // إذا كنا نعدل مسودة موجودة
    if (Number.isInteger(draftId)) {
      const formData = new FormData();

      formData.append(
        'draft_id',
        draftId
      );

      formData.append(
        'title',
        data.title
      );

      formData.append(
        'description',
        data.description
      );

      formData.append(
        'category',
        data.type
      );

      formData.append(
        'priority',
        data.priority
      );
      formData.append(
        'department',
        data.department
      );

      if (data.file) {
        formData.append(
          'attachment',
          data.file
        );
      }

      const saveResponse =
        await fetch(
          '/support/draft/save',
          {
            method: 'POST',
            body: formData
          }
        );

      const saveResult =
        await saveResponse.json();

      if (
        !saveResponse.ok ||
        !saveResult.success
      ) {
        showToast(
          saveResult.message ||
          'تعذر تحديث المسودة'
        );

        if (submitButton) {
          submitButton.disabled = false;
        }

        return;
      }

      const submitResponse =
        await fetch(
          '/support/draft/submit',
          {
            method: 'POST',

            headers: {
              'Content-Type':
                'application/json'
            },

            body: JSON.stringify({
              draft_id: draftId
            })
          }
        );

      const submitResult =
        await submitResponse.json();

      if (
        !submitResponse.ok ||
        !submitResult.success
      ) {
        showToast(
          submitResult.message ||
          'تعذر إرسال المسودة'
        );

        if (submitButton) {
          submitButton.disabled = false;
        }

        return;
      }

      showToast(
        `تم إنشاء طلبك بنجاح - ${submitResult.ticket_number}`,
        'success'
      );;

      setTimeout(() => {
        navigate('requests');
      }, 1500);

      return;
    }

    // إذا كان طلب جديد وليس مسودة
    const formData =
      new FormData();

    formData.append(
      'title',
      data.title
    );

    formData.append(
      'description',
      data.description
    );

    formData.append(
      'category',
      data.type
    );

    formData.append(
      'priority',
      data.priority
    );
    formData.append(
      'department',
      data.department
    );

    if (data.file) {
      formData.append(
        'attachment',
        data.file
      );
    }

    const response =
      await fetch(
        '/support/ticket/create',
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
        'تعذر إرسال الطلب'
      );

      if (submitButton) {
        submitButton.disabled = false;
      }

      return;
    }

    showToast(
      `تم إنشاء طلبك بنجاح - ${result.ticket_number}`,
      'success'
    );
    setTimeout(() => {
      navigate('requests');
    }, 1500);

  } catch (error) {
    console.error(
      'Create ticket error:',
      error
    );

    showToast(
      'حدث خطأ أثناء إرسال الطلب'
    );

    if (submitButton) {
      submitButton.disabled = false;
    }
  }
}
/*
   Ticket details
    */

async function renderDetail(id) {
  let ticket =
    getTicket(
      state,
      id
    );

  if (!ticket) {
    try {
      const response =
        await fetch(
          '/support/tickets'
        );

      const result =
        await response.json();

      if (
        !response.ok ||
        !result.success
      ) {
        showToast(
          'تعذر تحميل الطلب'
        );

        return;
      }

      state.tickets =
        (
          result.tickets || []
        ).filter(
          item =>
            item.status !==
            'مسودة'
        );

      ticket =
        getTicket(
          state,
          id
        );

    } catch (error) {
      console.error(
        'Load ticket detail error:',
        error
      );

      showToast(
        'حدث خطأ أثناء تحميل الطلب'
      );

      return;
    }
  }

  if (!ticket) {
    showToast(
      'لم يتم العثور على الطلب'
    );

    return navigate(
      'requests'
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

  const employeeAction =
    renderEmployeeAction(ticket);

  app.innerHTML = `
    <a
      class="page-back"
      href="#${detailReturnRoute}"
      id="back-to-requests"
    >

      ${icon('arrow')}

      العودة إلى الطلبات

    </a>


    <div class="record-card">

      ${renderTicketHero(ticket, [
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


        ${ticket.solution

      ? `
                <div
                  class="content-section workflow-card"
                >

                  <h2>
                    الحل المرسل
                  </h2>

                  <div class="solution-box">

                    <p class="solution-text">${escapeHTML(ticket.solution)}</p>

                    <small class="solution-meta">${escapeHTML(ticket.assignee || '')} — ${escapeHTML(formatDateTime(ticket.solutionAt))}</small>

                  </div>

                </div>
              `

      : ''
    }


        ${employeeAction

      ? `
                <div class="content-section">
                  ${employeeAction}
                </div>
              `

      : ''
    }

      </section>


      ${renderChat(
      ticket,
      'employee',
      ticket.status !== 'مغلق'
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
      'back-to-requests'
    )
    .addEventListener(
      'click',
      event => {

        event.preventDefault();


        navigate(
          detailReturnRoute
        );
      }
    );


  bindDetailActions(
    ticket
  );
  scrollChatToBottom();

  bindChat({
    ticket
  });
}
/*
   Employee actions
    */

function renderEmployeeAction(
  ticket
) {
  if (
    ticket.status ===
    'بانتظار تأكيد الموظف'
  ) {

    return `
      <div
        class="action-callout"
      >

        <h3>
          هل تم حل المشكلة؟
        </h3>


        <div
          class="action-row"
        >

          <button
            class="button"
            id="confirm-solution"
            type="button"
          >

            ${icon('check')}

            إغلاق الطلب

          </button>


          <button
            class="button danger-outline"
            id="problem-continues"
            type="button"
          >
            لا، المشكلة مستمرة
          </button>

        </div>

      </div>
    `;
  }


  if (
    ticket.status ===
    'مغلق'
  ) {

    return ticket.rating

      ? `
        <div
          class="action-callout"
        >

          <h3>
            تم إرسال تقييمك
          </h3>


          <p>

            ${'★'.repeat(
        ticket.rating.value
      )}


            ${ticket.rating.comment

        ? `
                  — ${escapeHTML(
          ticket.rating.comment
        )}
                `

        : ''
      }

          </p>

        </div>
      `


      : `
        <section
          class="rating-panel"
          id="rating-panel"
        >

          <h3>
            قيّم خدمة الدعم الفني
          </h3>

          <p>
            رأيك يساعد فريق الدعم على تحسين الخدمة
          </p>


          <div
            class="stars"
            aria-label="تقييم من خمس نجوم"
          >

            ${[
        5,
        4,
        3,
        2,
        1
      ]
        .map(
          value => `
                  <button
                    class="star-button"
                    type="button"
                    data-star="${value}"
                    aria-label="${value} نجوم"
                  >
                    ${icon('star')}
                  </button>
                `
        )
        .join('')}

          </div>


          <label
            for="rating-comment"
          >

            <b>
              ملاحظة التقييم
            </b>

            <span class="optional-label">
              (اختياري)
            </span>

          </label>


          <textarea
            class="field-control"
            id="rating-comment"
            placeholder="اكتب ملاحظتك عن الخدمة"
          ></textarea>


          <button
            class="button gold"
            id="submit-rating"
            type="button"
            disabled
          >
            إرسال التقييم
          </button>

        </section>
      `;
  }


  return '';
}


/* =========================================================
   Detail actions
   ========================================================= */

function bindDetailActions(
  ticket
) {
  document
    .getElementById(
      'confirm-solution'
    )
    ?.addEventListener(
      'click',
      async () => {

        await submitEmployeeAction(
          ticket,
          'confirm'
        );
      }
    );


  document
    .getElementById(
      'problem-continues'
    )
    ?.addEventListener(
      'click',
      async () => {

        await submitEmployeeAction(
          ticket,
          'reopen'
        );
      }
    );


  let rating =
    0;


  const stars = [
    ...document.querySelectorAll(
      '[data-star]'
    )
  ];


  const comment =
    document.getElementById(
      'rating-comment'
    );


  const submit =
    document.getElementById(
      'submit-rating'
    );


  const validate =
    () => {

      if (submit) {
        submit.disabled =
          !rating;
      }
    };


  stars.forEach(
    star =>

      star.addEventListener(
        'click',
        () => {

          rating =
            Number(
              star.dataset.star
            );


          stars.forEach(
            item =>

              item.classList.toggle(
                'selected',

                Number(
                  item.dataset.star
                ) <= rating
              )
          );


          validate();
        }
      )
  );


  submit
    ?.addEventListener(
      'click',
      async () => {

        if (!rating) {
          return;
        }


        try {
          const response =
            await fetch(
              '/support/ticket/rating',
              {
                method:
                  'POST',

                headers: {
                  'Content-Type':
                    'application/json'
                },


                body:
                  JSON.stringify({
                    ticket_number:
                      ticket.id,


                    rating:
                      rating,


                    comment:
                      comment
                        ?.value
                        .trim() ||
                      ''
                  })
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
              'تعذر إرسال التقييم'
            );

            return;
          }


          showToast(
            result.message ||
            'تم إرسال التقييم بنجاح',
            'success'
          );

          const responseTickets =
            await fetch(
              '/support/tickets'
            );


          const ticketsResult =
            await responseTickets
              .json();


          if (
            responseTickets.ok &&
            ticketsResult.success
          ) {

            state.tickets =
              ticketsResult.tickets ||
              [];
          }


          navigate(
            'requests'
          );


        } catch (error) {

          console.error(
            'Rating error:',
            error
          );


          showToast(
            'حدث خطأ أثناء إرسال التقييم'
          );
        }
      }
    );
}


/*
   Confirm / reopen ticket in Odoo
    */

async function submitEmployeeAction(
  ticket,
  action
) {
  try {

    const response =
      await fetch(
        '/support/ticket/employee-action',
        {
          method:
            'POST',


          headers: {
            'Content-Type':
              'application/json'
          },


          body:
            JSON.stringify({
              ticket_number:
                ticket.id,


              action:
                action
            })
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
        'تعذر تنفيذ الإجراء'
      );

      return;
    }


    showToast(
      result.message,
      'success'
    );

    const responseTickets =
      await fetch(
        '/support/tickets'
      );


    const ticketsResult =
      await responseTickets
        .json();


    if (
      responseTickets.ok &&
      ticketsResult.success
    ) {

      state.tickets =
        ticketsResult.tickets ||
        [];
    }

    navigate(
      'detail',
      ticket.id
    );


  } catch (error) {

    console.error(
      'Employee action error:',
      error
    );

    showToast(
      'حدث خطأ أثناء تنفيذ الإجراء'
    );
  }
}
/*
   Browser navigation
    */

if (isEmployeePage) {

  /* يحصر تنسيقات المنصة في صفحاتها ولا يمسّ بقية موقع Odoo */
  document.body.classList.add('iu-portal');

  window.addEventListener(
    'hashchange',
    () => {

      const nextRoute =
        readRoute(
          'requests'
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