const STORAGE_KEYS = {
  language: "tradenodex.language",
  currency: "tradenodex.currency",
  density: "tradenodex.density",
  fontScale: "tradenodex.fontScale",
  motion: "tradenodex.motion",
};

const DEFAULT_LANGUAGE = "en";
const DEFAULT_CURRENCY = "USD";

const state = {
  dashboard: null,
  positions: [],
  logsPage: null,
  liveSnapshot: null,
  liveSocket: null,
  liveHeartbeat: null,
  currentSignalId: null,
  currentCopyTradeId: null,
  currentLogId: null,
  lastExecutionResponse: null,
  currentAuditTaskId: null,
  instruments: {
    BINANCE: [],
    BYBIT: [],
    OKX: [],
    COINBASE: [],
    KRAKEN: [],
    BITMEX: [],
    GATEIO: [],
  },
  preferences: {
    language: localStorage.getItem(STORAGE_KEYS.language) || DEFAULT_LANGUAGE,
    currency: localStorage.getItem(STORAGE_KEYS.currency) || DEFAULT_CURRENCY,
    density: localStorage.getItem(STORAGE_KEYS.density) || "standard",
    fontScale: localStorage.getItem(STORAGE_KEYS.fontScale) || "default",
    motion: localStorage.getItem(STORAGE_KEYS.motion) || "full",
  },
  logs: {
    page: 1,
    limit: 100,
    exchange: "",
    log_type: "",
    search: "",
    linked_task_id: "",
    sort_by: "timestamp",
    sort_order: "desc",
  },
};

const LANGUAGE_OPTIONS = [
  { code: "zh-CN", label: "简体中文", locale: "zh-CN", dir: "ltr", tier: "Tier 1" },
  { code: "xerca", label: "xərcə", locale: "az-Latn-AZ", dir: "ltr", tier: "Tier 3" },
  { code: "ar", label: "العربية", locale: "ar", dir: "rtl", tier: "Tier 2" },
  { code: "ar-eu", label: "أوروبية", locale: "ar", dir: "rtl", tier: "Tier 3" },
  { code: "az", label: "Azərbaycan", locale: "az-Latn-AZ", dir: "ltr", tier: "Tier 3" },
  { code: "bg", label: "български", locale: "bg-BG", dir: "ltr", tier: "Tier 3" },
  { code: "valjan", label: "ваљан", locale: "sr-Cyrl-RS", dir: "ltr", tier: "Tier 3" },
  { code: "cs", label: "Čeština", locale: "cs-CZ", dir: "ltr", tier: "Tier 3" },
  { code: "da", label: "Dansk", locale: "da-DK", dir: "ltr", tier: "Tier 3" },
  { code: "de-CH", label: "Deutsch (Schweiz)", locale: "de-CH", dir: "ltr", tier: "Tier 2" },
  { code: "el", label: "Ελληνικά", locale: "el-GR", dir: "ltr", tier: "Tier 3" },
  { code: "en", label: "English", locale: "en-US", dir: "ltr", tier: "Tier 1" },
  { code: "en-IN", label: "English (India)", locale: "en-IN", dir: "ltr", tier: "Tier 3" },
  { code: "en-AF", label: "English (Africa)", locale: "en-ZA", dir: "ltr", tier: "Tier 3" },
  { code: "en-KZ", label: "English (Kazakhstan)", locale: "en-KZ", dir: "ltr", tier: "Tier 3" },
  { code: "en-JP", label: "English (Japan)", locale: "en-JP", dir: "ltr", tier: "Tier 3" },
  { code: "en-TR", label: "English (Türkiye)", locale: "en-TR", dir: "ltr", tier: "Tier 3" },
  { code: "es-419", label: "Español (Latinoamérica)", locale: "es-419", dir: "ltr", tier: "Tier 2" },
  { code: "es-ES", label: "Español (España)", locale: "es-ES", dir: "ltr", tier: "Tier 3" },
  { code: "es-AR", label: "Español (Argentina)", locale: "es-AR", dir: "ltr", tier: "Tier 3" },
  { code: "fr-FR", label: "Français", locale: "fr-FR", dir: "ltr", tier: "Tier 2" },
  { code: "fr-AF", label: "Français (Afrique)", locale: "fr-CI", dir: "ltr", tier: "Tier 3" },
  { code: "hr", label: "Hrvatski", locale: "hr-HR", dir: "ltr", tier: "Tier 3" },
  { code: "hu", label: "magyar nyelv", locale: "hu-HU", dir: "ltr", tier: "Tier 3" },
  { code: "id", label: "Bahasa Indonesia", locale: "id-ID", dir: "ltr", tier: "Tier 3" },
  { code: "it", label: "Italiano", locale: "it-IT", dir: "ltr", tier: "Tier 3" },
  { code: "kk", label: "Казакша", locale: "kk-KZ", dir: "ltr", tier: "Tier 3" },
  { code: "talaluya", label: "талалӱя", locale: "ru-RU", dir: "ltr", tier: "Tier 3" },
  { code: "ky", label: "Кыргыз", locale: "ky-KG", dir: "ltr", tier: "Tier 3" },
  { code: "aga", label: "ага", locale: "ru-RU", dir: "ltr", tier: "Tier 3" },
  { code: "lt", label: "Lietuvių", locale: "lt-LT", dir: "ltr", tier: "Tier 3" },
  { code: "lv", label: "latviešu valoda", locale: "lv-LV", dir: "ltr", tier: "Tier 3" },
  { code: "udg", label: "Үдгэһэх", locale: "ru-RU", dir: "ltr", tier: "Tier 3" },
  { code: "pl", label: "Polski", locale: "pl-PL", dir: "ltr", tier: "Tier 3" },
  { code: "pt-BR", label: "Português (Brasil)", locale: "pt-BR", dir: "ltr", tier: "Tier 2" },
  { code: "pt-PT", label: "Português (Portugal)", locale: "pt-PT", dir: "ltr", tier: "Tier 3" },
  { code: "pt-AO", label: "Português (Angola)", locale: "pt-AO", dir: "ltr", tier: "Tier 3" },
  { code: "ro", label: "Română", locale: "ro-RO", dir: "ltr", tier: "Tier 3" },
  { code: "ru", label: "Русский", locale: "ru-RU", dir: "ltr", tier: "Tier 2" },
  { code: "ru-KZ", label: "Русский (Казахстан)", locale: "ru-KZ", dir: "ltr", tier: "Tier 3" },
  { code: "booch", label: "Боочч", locale: "ru-RU", dir: "ltr", tier: "Tier 3" },
  { code: "sk", label: "Slovenčina", locale: "sk-SK", dir: "ltr", tier: "Tier 3" },
  { code: "sl", label: "Slovenščina", locale: "sl-SI", dir: "ltr", tier: "Tier 3" },
  { code: "sv", label: "svenska", locale: "sv-SE", dir: "ltr", tier: "Tier 3" },
  { code: "uk", label: "Українська", locale: "uk-UA", dir: "ltr", tier: "Tier 3" },
  { code: "uz", label: "O‘zbekcha", locale: "uz-Latn-UZ", dir: "ltr", tier: "Tier 3" },
  { code: "vi", label: "Tiếng Việt", locale: "vi-VN", dir: "ltr", tier: "Tier 3" },
  { code: "zh-TW", label: "繁體中文", locale: "zh-TW", dir: "ltr", tier: "Tier 2" },
];

const CURRENCY_OPTIONS = [
  ["CNY", "人民币"], ["USD", "美元"], ["EUR", "欧元"], ["AED", "UAE dirham"], ["ARS", "Argentine Peso"],
  ["AUD", "Australian Dollar"], ["AZN", "Azerbaijan Manat"], ["BDT", "Bangladesh Taka"], ["BGN", "Bulgarian Lev"], ["BHD", "Bahraini Dinar"],
  ["BOB", "Bolivian Boliviano"], ["BRL", "Brazilian Real"], ["CAD", "Canadian Dollar"], ["CHF", "Swiss Franc"], ["CLP", "Chilean Peso"],
  ["COP", "Colombian Peso"], ["CZK", "Czech Koruna"], ["DKK", "Danish Krone"], ["EGP", "Egyptian Pound"], ["GBP", "Pound Sterling"],
  ["HKD", "Hong Kong Dollar"], ["HRK", "Croatian Kuna"], ["HUF", "Hungarian Forint"], ["IDR", "Indonesian Rupiah"], ["INR", "Indian Rupee"],
  ["JPY", "Japanese Yen"], ["KES", "Kenyan Shilling"], ["KWD", "Kuwaiti Dinar"], ["KZT", "Kazakhstan Tenge"], ["MAD", "Moroccan Dirham"],
  ["MNT", "Mongolian Tugrik"], ["MXN", "Mexican Peso"], ["NZD", "New Zealand Dollar"], ["OMR", "Omani Rial"], ["PEN", "Nuevo Sol"],
  ["PHP", "Philippine Peso"], ["PKR", "Pakistani Rupee"], ["PLN", "Polish Zloty"], ["QAR", "Qatari Riyal"], ["RON", "Romanian Leu"],
  ["RUB", "Russian Ruble"], ["SAR", "Saudi Riyal"], ["SEK", "Swedish Krona"], ["THB", "Thai Baht"], ["TRY", "Turkish Lira"],
  ["TWD", "New Taiwan dollar"], ["UAH", "Ukrainian Hryvnia"], ["UGX", "Uganda Shilling"], ["UZS", "Uzbekistani Sum"], ["VES", "Venezuelan Bolivar"],
  ["VND", "Vietnamese Dong"], ["ZAR", "South African Rand"],
].map(([code, name]) => ({ code, name }));

const TRANSLATIONS = {
  en: {
    "brand.kicker": "TradeNodeX",
    "brand.wordmark": "TRADENODEX",
    "brand.subline": "Institutional Digital Asset Gateway",
    "topbar.connectivity": "Connectivity",
    "topbar.stream": "Realtime Stream",
    "topbar.operator": "Operator",
    "toolbar.searchLabel": "Workspace Search",
    "toolbar.searchPlaceholder": "Search signals, accounts, symbols, logs",
    "toolbar.searchAction": "Find",
    "toolbar.language": "Language",
    "toolbar.currency": "Display Currency",
    "toolbar.density": "Density",
    "toolbar.fontScale": "Font Scale",
    "toolbar.motion": "Motion",
    "status.liveOffline": "Realtime stream offline",
    "signals.title": "Operational Signals",
    "signals.subtitle": "Terminal-grade signal cards with routing readiness and direct execution entry.",
    "signals.modalKicker": "Signal Registry",
    "signals.sourceAccount": "Source Account",
    "signals.defaultCopyMode": "Default Copy Mode",
    "signals.defaultScale": "Default Scale",
    "signals.defaultLeverage": "Default Leverage",
    "copyTrades.title": "Copy Routing",
    "copyTrades.subtitle": "Route design, 1:1 exact emphasis, execution templates, and operator controls.",
    "copyTrades.empty": "Select a copy trade to edit command template, mode, and risk constraints.",
    "copyTrades.baseBinding": "Base Binding",
    "copyTrades.baseBindingNote": "Primary route mapping between signal source and follower account.",
    "copyTrades.modeSection": "Copy Mode",
    "copyTrades.modeSectionNote": "Exact mode is visually emphasized and scale is conditional.",
    "copyTrades.exactNote": "Follower mirrors the source quantity and constraints.",
    "copyTrades.scaleMode": "Scale",
    "copyTrades.scaleNote": "Follower applies a quantity multiplier.",
    "copyTrades.executionTemplate": "Execution Template",
    "copyTrades.tradeCommand": "Trade Command",
    "copyTrades.riskNotes": "Risk & Operator Notes",
    "copyTrades.riskNotesNote": "Use this as controlled operating instructions and audit context.",
    "copyTrades.notesPlaceholder": "Execution rules, risk constraints, and operator notes",
    "copyTrades.scaleFactor": "Scale Factor",
    "copyTrades.overrideLeverage": "Override Leverage",
    "registry.title": "API Registry",
    "registry.subtitle": "Signal masters and follower credentials with readiness dimensions and security guidance.",
    "registry.signalSources": "Signal Sources",
    "registry.apiAccounts": "API Accounts",
    "registry.apiAccount": "API Account",
    "registry.readiness": "Readiness",
    "registry.modalKicker": "API Accounts",
    "registry.apiKey": "API Key",
    "registry.apiSecret": "API Secret",
    "registry.apiPassphrase": "API Passphrase",
    "registry.masterApiKey": "Master API Key",
    "registry.masterApiSecret": "Master API Secret",
    "registry.masterApiPassphrase": "Master API Passphrase",
    "registry.passphraseHint": "Required for OKX when enabled",
    "registry.securityTitle": "Credential Operating Rules",
    "registry.ruleTradeOnly": "Enable trade permissions only.",
    "registry.ruleNoWithdrawals": "Never enable withdrawals.",
    "registry.ruleWhitelist": "Use recommended IP whitelist where supported.",
    "registry.ruleOkxPassphrase": "OKX requires API passphrase.",
    "registry.ruleEncrypted": "Credentials are stored encrypted at rest.",
    "registry.encryptedHint": "Sensitive fields are encrypted at rest and should not include withdrawal rights.",
    "metrics.runtimeTitle": "Runtime",
    "metrics.runtimeSubtitle": "Signals, routing, followers, and live audit throughput.",
    "metrics.performanceTitle": "Performance",
    "metrics.performanceSubtitle": "Display-currency analytics for exposure, pnl, and fills.",
    "tabs.signals": "Signals",
    "tabs.copyTrades": "Copy Routing",
    "tabs.apiRegistry": "API Registry",
    "tabs.studio": "Studio",
    "tabs.logs": "Audit Logs",
    "tabs.positions": "Equity List",
    "studio.presetName": "Preset Name",
    "studio.presetPlaceholder": "Signal Builder Profile",
    "studio.orderType": "Order Type",
    "studio.price": "Price",
    "studio.stopPrice": "Stop Price",
    "studio.orderEntry": "Order Entry",
    "studio.executionControls": "Execution Controls",
    "studio.riskControls": "Risk Controls",
    "studio.quantity.absolute": "Use absolute value",
    "studio.quantity.available": "Use percent (Available Balance)",
    "studio.quantity.wallet": "Use percent (Wallet)",
    "studio.quantity.risk": "Risk %",
    "studio.quantity.copyTrader": "Use from copy trader",
    "studio.units": "Units / Cost",
    "studio.leverage": "Leverage",
    "studio.marginMode": "Margin Mode",
    "studio.stopLoss": "Stop Loss %",
    "studio.delaySeconds": "Delay Seconds",
    "studio.hedgeMode": "Hedge Mode",
    "studio.preventPyramiding": "Prevent Pyramiding",
    "studio.cancelPendingOrders": "Cancel Pending Orders",
    "studio.closeProfitOnly": "Only Close in Profit",
    "studio.broadcastTrade": "Broadcast Trade",
    "studio.createCopySignal": "Create copy-trade signal",
    "studio.useDca": "Use DCA",
    "studio.cancelScope": "Cancel Scope",
    "studio.cancelScopeNote": "Clear working orders without changing the current position.",
    "studio.cancelAll": "Cancel all orders",
    "studio.cancelDca": "Cancel DCA orders",
    "studio.closeScope": "Close Position Scope",
    "studio.closeScopeNote": "Target the full book, long-only, short-only, or partial close logic.",
    "studio.closeAll": "Close All",
    "studio.closeLong": "Close Long",
    "studio.closeShort": "Close Short",
    "studio.partialClose": "Partial Close",
    "studio.closeByLimit": "Close by limit order",
    "studio.closeCurrentPosition": "Close Current Position",
    "studio.takeProfitSteps": "Take-Profit Steps",
    "studio.savedPresets": "Saved Builder Presets",
    "studio.liveQueue": "Live Execution Queue",
    "studio.liveQueueWaiting": "Waiting for realtime snapshots.",
    "studio.generatedCommand": "Generated Command",
    "studio.lastExecutionResponse": "Last Execution Response",
    "studio.commandPlaceholder": "Generated TradeNodeX command JSON",
    "studio.latency": "Latency",
    "studio.auditTrail": "Execution Audit Trail",
    "studio.attemptTimeline": "Attempt Timeline",
    "studio.relatedLogs": "Related Logs",
    "logs.title": "Audit Logs",
    "logs.subtitle": "Structured severity, quick filters, detail inspector, and PnL analysis.",
    "logs.detailTitle": "Log Detail",
    "logs.selectLog": "Select a log entry to inspect raw details, linked ids, and exchange responses.",
    "positions.title": "Equity List",
    "positions.subtitle": "Exposure, unrealized pnl, leverage, freshness, and display-currency notional analytics.",
    "actions.refresh": "Refresh",
    "actions.refreshLogs": "Refresh Logs",
    "actions.addSignal": "Add Signal",
    "actions.addCopyTrade": "Add Copy Trade",
    "actions.addApiAccount": "Add API Account",
    "actions.save": "Save",
    "actions.saveSignal": "Save Signal",
    "actions.saveApiAccount": "Save API Account",
    "actions.delete": "Delete",
    "actions.copy": "Copy",
    "actions.apply": "Apply",
    "actions.latest": "Latest",
    "actions.back": "Back",
    "actions.validateApi": "Validate API",
    "actions.generateCopyTrade": "Generate Copy-Trade",
    "actions.executeNow": "Execute now!",
    "actions.addTakeProfit": "Add Take-Profit-Step",
    "actions.sync": "Sync",
    "actions.toggleTemplate": "Toggle Template",
    "actions.edit": "Edit",
    "actions.validate": "Validate",
    "actions.pause": "Pause",
    "actions.resume": "Resume",
    "table.name": "Name",
    "table.signal": "Signal",
    "table.exchange": "Exchange",
    "table.pairs": "Pairs",
    "table.validation": "Validation",
    "table.mode": "Mode",
    "table.status": "Status",
    "table.enabled": "Enabled",
    "table.key": "Key",
    "table.pnl": "PnL",
    "table.message": "Message",
    "table.timestamp": "Timestamp",
    "table.type": "Type",
    "table.instrument": "Instrument",
    "table.entry": "Entry",
    "table.quantity": "Quantity",
    "table.captured": "Captured",
    "table.signalSource": "Signal Source",
    "table.created": "Created",
    "table.pair": "Pair",
    "table.symbol": "Symbol",
    "table.action": "Action",
    "table.queue": "Queue",
    "table.exposure": "Exposure",
    "table.leverage": "Leverage",
    "table.freshness": "Freshness",
    "filters.searchLogs": "Search logs",
    "metrics.followers": "Followers",
    "common.environment": "Environment",
    "common.description": "Description",
    "common.notes": "Notes",
    "common.optional": "Optional",
    "footer.version": "Institutional Digital Asset Gateway v4.3-terminal",
  },
  "zh-CN": {
    "brand.kicker": "TradeNodeX",
    "brand.wordmark": "TRADENODEX",
    "brand.subline": "机构级数字资产控制终端",
    "topbar.connectivity": "连接状态",
    "topbar.stream": "实时流",
    "topbar.operator": "操作员",
    "toolbar.searchLabel": "工作台搜索",
    "toolbar.searchPlaceholder": "搜索信号、账户、交易对、日志",
    "toolbar.searchAction": "查找",
    "toolbar.language": "语言",
    "toolbar.currency": "显示币种",
    "toolbar.density": "密度",
    "toolbar.fontScale": "字号",
    "toolbar.motion": "动效",
    "status.liveOffline": "实时流离线",
    "signals.title": "运行中信号",
    "copyTrades.title": "跟单路由",
    "registry.title": "API 注册表",
    "tabs.signals": "信号",
    "tabs.copyTrades": "跟单路由",
    "tabs.apiRegistry": "API 注册表",
    "tabs.studio": "执行工作台",
    "tabs.logs": "审计日志",
    "tabs.positions": "权益列表",
    "logs.title": "审计日志",
    "positions.title": "权益列表",
    "actions.refresh": "刷新",
    "actions.save": "保存",
    "actions.delete": "删除",
    "actions.copy": "复制",
    "actions.back": "返回",
    "actions.edit": "编辑",
    "actions.validate": "校验",
    "actions.pause": "暂停",
    "actions.resume": "恢复",
    "table.symbol": "标的",
    "filters.searchLogs": "搜索日志",
  },
};

const TIER2_TRANSLATION_OVERRIDES = {
  "zh-TW": {
    "brand.subline": "機構級數位資產控制終端",
    "topbar.connectivity": "連線狀態",
    "topbar.stream": "即時流",
    "topbar.operator": "操作員",
    "toolbar.searchLabel": "工作台搜尋",
    "toolbar.searchPlaceholder": "搜尋信號、帳戶、交易對、日誌",
    "toolbar.searchAction": "查找",
    "toolbar.language": "語言",
    "toolbar.currency": "顯示幣種",
    "toolbar.density": "密度",
    "toolbar.fontScale": "字級",
    "toolbar.motion": "動效",
    "status.liveOffline": "即時流離線",
    "signals.title": "運行中信號",
    "signals.subtitle": "具備路由就緒度與快速執行入口的終端信號卡。",
    "copyTrades.title": "跟單路由",
    "copyTrades.subtitle": "路由設計、1:1 精確跟單、執行模板與風險備註。",
    "registry.title": "API 註冊表",
    "registry.subtitle": "主信號與子帳戶憑證、就緒狀態與安全規則。",
    "tabs.signals": "信號",
    "tabs.copyTrades": "跟單路由",
    "tabs.apiRegistry": "API 註冊表",
    "tabs.studio": "執行工作台",
    "tabs.logs": "審計日誌",
    "tabs.positions": "權益列表",
    "logs.title": "審計日誌",
    "logs.subtitle": "結構化嚴重級別、快速篩選與明細檢視。",
    "positions.title": "權益列表",
    "positions.subtitle": "曝光、未實現盈虧、槓桿與快照新鮮度。",
    "actions.refresh": "刷新",
    "actions.save": "儲存",
    "actions.delete": "刪除",
    "actions.copy": "複製",
    "actions.back": "返回",
    "actions.edit": "編輯",
    "actions.validate": "驗證",
    "actions.pause": "暫停",
    "actions.resume": "恢復",
  },
  ar: {
    "brand.subline": "بوابة مؤسسية للتحكم في الأصول الرقمية",
    "topbar.connectivity": "الاتصال",
    "topbar.stream": "التدفق اللحظي",
    "topbar.operator": "المشغّل",
    "toolbar.searchLabel": "بحث مساحة العمل",
    "toolbar.searchPlaceholder": "ابحث عن الإشارات أو الحسابات أو الأزواج أو السجلات",
    "toolbar.searchAction": "بحث",
    "toolbar.language": "اللغة",
    "toolbar.currency": "عملة العرض",
    "toolbar.density": "الكثافة",
    "toolbar.fontScale": "حجم الخط",
    "toolbar.motion": "الحركة",
    "status.liveOffline": "التدفق اللحظي غير متصل",
    "signals.title": "الإشارات التشغيلية",
    "copyTrades.title": "توجيه النسخ",
    "registry.title": "سجل API",
    "tabs.signals": "الإشارات",
    "tabs.copyTrades": "توجيه النسخ",
    "tabs.apiRegistry": "سجل API",
    "tabs.studio": "الاستوديو",
    "tabs.logs": "سجلات التدقيق",
    "tabs.positions": "قائمة حقوق الملكية",
    "logs.title": "سجلات التدقيق",
    "positions.title": "قائمة حقوق الملكية",
    "actions.refresh": "تحديث",
    "actions.save": "حفظ",
    "actions.delete": "حذف",
    "actions.copy": "نسخ",
    "actions.back": "رجوع",
    "actions.edit": "تحرير",
    "actions.validate": "تحقق",
    "actions.pause": "إيقاف",
    "actions.resume": "استئناف",
  },
  ru: {
    "brand.subline": "Институциональный терминал контроля цифровых активов",
    "topbar.connectivity": "Связь",
    "topbar.stream": "Поток в реальном времени",
    "topbar.operator": "Оператор",
    "toolbar.searchLabel": "Поиск по рабочему пространству",
    "toolbar.searchPlaceholder": "Поиск сигналов, счетов, пар и логов",
    "toolbar.searchAction": "Найти",
    "toolbar.language": "Язык",
    "toolbar.currency": "Валюта отображения",
    "toolbar.density": "Плотность",
    "toolbar.fontScale": "Размер шрифта",
    "toolbar.motion": "Анимация",
    "status.liveOffline": "Поток в реальном времени отключен",
    "signals.title": "Торговые сигналы",
    "copyTrades.title": "Маршрутизация копирования",
    "registry.title": "Реестр API",
    "tabs.signals": "Сигналы",
    "tabs.copyTrades": "Маршруты копирования",
    "tabs.apiRegistry": "Реестр API",
    "tabs.studio": "Студия",
    "tabs.logs": "Журнал аудита",
    "tabs.positions": "Список капитала",
    "logs.title": "Журнал аудита",
    "positions.title": "Список капитала",
    "actions.refresh": "Обновить",
    "actions.save": "Сохранить",
    "actions.delete": "Удалить",
    "actions.copy": "Копировать",
    "actions.back": "Назад",
    "actions.edit": "Редактировать",
    "actions.validate": "Проверить",
    "actions.pause": "Пауза",
    "actions.resume": "Возобновить",
  },
  "es-419": {
    "brand.subline": "Centro institucional de control de activos digitales",
    "topbar.connectivity": "Conectividad",
    "topbar.stream": "Flujo en tiempo real",
    "topbar.operator": "Operador",
    "toolbar.searchLabel": "Búsqueda del espacio de trabajo",
    "toolbar.searchPlaceholder": "Buscar señales, cuentas, pares y registros",
    "toolbar.searchAction": "Buscar",
    "toolbar.language": "Idioma",
    "toolbar.currency": "Moneda de visualización",
    "toolbar.density": "Densidad",
    "toolbar.fontScale": "Escala tipográfica",
    "toolbar.motion": "Movimiento",
    "status.liveOffline": "Flujo en tiempo real desconectado",
    "signals.title": "Señales operativas",
    "copyTrades.title": "Ruteo de copiado",
    "registry.title": "Registro API",
    "tabs.signals": "Señales",
    "tabs.copyTrades": "Ruteo de copiado",
    "tabs.apiRegistry": "Registro API",
    "tabs.studio": "Studio",
    "tabs.logs": "Logs de auditoría",
    "tabs.positions": "Lista de equity",
    "logs.title": "Logs de auditoría",
    "positions.title": "Lista de equity",
    "actions.refresh": "Actualizar",
    "actions.save": "Guardar",
    "actions.delete": "Eliminar",
    "actions.copy": "Copiar",
    "actions.back": "Volver",
    "actions.edit": "Editar",
    "actions.validate": "Validar",
    "actions.pause": "Pausar",
    "actions.resume": "Reanudar",
  },
  "fr-FR": {
    "brand.subline": "Terminal institutionnel de contrôle des actifs numériques",
    "topbar.connectivity": "Connectivité",
    "topbar.stream": "Flux temps réel",
    "topbar.operator": "Opérateur",
    "toolbar.searchLabel": "Recherche espace de travail",
    "toolbar.searchPlaceholder": "Rechercher signaux, comptes, paires et journaux",
    "toolbar.searchAction": "Rechercher",
    "toolbar.language": "Langue",
    "toolbar.currency": "Devise d’affichage",
    "toolbar.density": "Densité",
    "toolbar.fontScale": "Taille de police",
    "toolbar.motion": "Animations",
    "status.liveOffline": "Flux temps réel hors ligne",
    "signals.title": "Signaux opérationnels",
    "copyTrades.title": "Routage de copie",
    "registry.title": "Registre API",
    "tabs.signals": "Signaux",
    "tabs.copyTrades": "Routage de copie",
    "tabs.apiRegistry": "Registre API",
    "tabs.studio": "Studio",
    "tabs.logs": "Journaux d’audit",
    "tabs.positions": "Liste d’équité",
    "logs.title": "Journaux d’audit",
    "positions.title": "Liste d’équité",
    "actions.refresh": "Actualiser",
    "actions.save": "Enregistrer",
    "actions.delete": "Supprimer",
    "actions.copy": "Copier",
    "actions.back": "Retour",
    "actions.edit": "Modifier",
    "actions.validate": "Valider",
    "actions.pause": "Pause",
    "actions.resume": "Reprendre",
  },
  "de-CH": {
    "brand.subline": "Institutionelles Kontrollterminal für digitale Vermögenswerte",
    "topbar.connectivity": "Konnektivität",
    "topbar.stream": "Echtzeit-Stream",
    "topbar.operator": "Operator",
    "toolbar.searchLabel": "Workspace-Suche",
    "toolbar.searchPlaceholder": "Signale, Konten, Paare und Logs suchen",
    "toolbar.searchAction": "Suchen",
    "toolbar.language": "Sprache",
    "toolbar.currency": "Anzeigewährung",
    "toolbar.density": "Dichte",
    "toolbar.fontScale": "Schriftgrad",
    "toolbar.motion": "Bewegung",
    "status.liveOffline": "Echtzeit-Stream offline",
    "signals.title": "Operative Signale",
    "copyTrades.title": "Copy-Routing",
    "registry.title": "API-Register",
    "tabs.signals": "Signale",
    "tabs.copyTrades": "Copy-Routing",
    "tabs.apiRegistry": "API-Register",
    "tabs.studio": "Studio",
    "tabs.logs": "Audit-Logs",
    "tabs.positions": "Equity-Liste",
    "logs.title": "Audit-Logs",
    "positions.title": "Equity-Liste",
    "actions.refresh": "Aktualisieren",
    "actions.save": "Speichern",
    "actions.delete": "Löschen",
    "actions.copy": "Kopieren",
    "actions.back": "Zurück",
    "actions.edit": "Bearbeiten",
    "actions.validate": "Prüfen",
    "actions.pause": "Pausieren",
    "actions.resume": "Fortsetzen",
  },
  "pt-BR": {
    "brand.subline": "Terminal institucional de controle de ativos digitais",
    "topbar.connectivity": "Conectividade",
    "topbar.stream": "Fluxo em tempo real",
    "topbar.operator": "Operador",
    "toolbar.searchLabel": "Busca do workspace",
    "toolbar.searchPlaceholder": "Buscar sinais, contas, pares e logs",
    "toolbar.searchAction": "Buscar",
    "toolbar.language": "Idioma",
    "toolbar.currency": "Moeda de exibição",
    "toolbar.density": "Densidade",
    "toolbar.fontScale": "Escala da fonte",
    "toolbar.motion": "Movimento",
    "status.liveOffline": "Fluxo em tempo real offline",
    "signals.title": "Sinais operacionais",
    "copyTrades.title": "Roteamento de cópia",
    "registry.title": "Registro de API",
    "tabs.signals": "Sinais",
    "tabs.copyTrades": "Roteamento de cópia",
    "tabs.apiRegistry": "Registro de API",
    "tabs.studio": "Studio",
    "tabs.logs": "Logs de auditoria",
    "tabs.positions": "Lista de equity",
    "logs.title": "Logs de auditoria",
    "positions.title": "Lista de equity",
    "actions.refresh": "Atualizar",
    "actions.save": "Salvar",
    "actions.delete": "Excluir",
    "actions.copy": "Copiar",
    "actions.back": "Voltar",
    "actions.edit": "Editar",
    "actions.validate": "Validar",
    "actions.pause": "Pausar",
    "actions.resume": "Retomar",
  },
};

Object.entries(TIER2_TRANSLATION_OVERRIDES).forEach(([code, overrides]) => {
  TRANSLATIONS[code] = {
    ...TRANSLATIONS.en,
    ...overrides,
  };
});

const EXCHANGE_META = {
  BINANCE: {
    title: "TradeNodeX Binance Futures",
    api: "https://www.binance.com/en/my/settings/api-management",
    guide: "https://www.binance.com/en/support/faq",
    register: "https://www.binance.com/",
    products: [{ value: "USD_M", label: "USD-M Futures" }, { value: "COIN_M", label: "COIN-M Futures" }],
  },
  BYBIT: {
    title: "TradeNodeX Bybit Futures",
    api: "https://www.bybit.com/app/user/api-management",
    guide: "https://www.bybit.com/en/help-center/",
    register: "https://www.bybit.com/",
    products: [{ value: "FUTURES", label: "Futures" }, { value: "SPOT", label: "Spot" }],
  },
  OKX: {
    title: "TradeNodeX OKX Derivatives",
    api: "https://www.okx.com/account/my-api",
    guide: "https://www.okx.com/help",
    register: "https://www.okx.com/",
    products: [{ value: "SWAP", label: "Swap" }, { value: "FUTURES", label: "Futures" }],
  },
  COINBASE: {
    title: "TradeNodeX Coinbase Advanced",
    api: "https://www.coinbase.com/settings/api",
    guide: "https://help.coinbase.com/",
    register: "https://www.coinbase.com/",
    products: [{ value: "ADVANCED", label: "Advanced" }, { value: "SPOT", label: "Spot" }],
  },
  KRAKEN: {
    title: "TradeNodeX Kraken Futures",
    api: "https://pro.kraken.com/app/settings/api",
    guide: "https://support.kraken.com/",
    register: "https://www.kraken.com/",
    products: [{ value: "FUTURES", label: "Futures" }, { value: "SPOT", label: "Spot" }],
  },
  BITMEX: {
    title: "TradeNodeX BitMEX Derivatives",
    api: "https://www.bitmex.com/app/apiKeys",
    guide: "https://support.bitmex.com/",
    register: "https://www.bitmex.com/",
    products: [{ value: "PERPETUAL", label: "Perpetual" }, { value: "FUTURES", label: "Futures" }],
  },
  GATEIO: {
    title: "TradeNodeX Gate.io Futures",
    api: "https://www.gate.io/myaccount/apiv4keys",
    guide: "https://www.gate.io/help",
    register: "https://www.gate.io/",
    products: [{ value: "FUTURES", label: "Futures" }, { value: "SPOT", label: "Spot" }],
  },
};

const QUICK_LOG_TYPES = ["ALL", "INFO", "WARNING", "ERROR", "EXECUTION", "RECONCILE", "MANUAL", "SIGNAL"];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getLanguageOption(code = state.preferences.language) {
  return LANGUAGE_OPTIONS.find((item) => item.code === code) || LANGUAGE_OPTIONS.find((item) => item.code === DEFAULT_LANGUAGE);
}

function getCurrencyOption(code = state.preferences.currency) {
  return CURRENCY_OPTIONS.find((item) => item.code === code) || CURRENCY_OPTIONS.find((item) => item.code === DEFAULT_CURRENCY);
}

function t(key, variables = {}) {
  const lang = getLanguageOption().code;
  const translation = TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en[key] ?? key;
  return Object.entries(variables).reduce((acc, [token, value]) => acc.replaceAll(`{${token}}`, String(value)), translation);
}

function persistPreferences() {
  Object.entries(state.preferences).forEach(([key, value]) => localStorage.setItem(STORAGE_KEYS[key], value));
}

function applyDocumentPreferences() {
  const language = getLanguageOption();
  document.documentElement.lang = language.code;
  document.body.dir = language.dir;
  document.body.dataset.density = state.preferences.density;
  document.body.dataset.fontScale = state.preferences.fontScale;
  document.body.dataset.motion = state.preferences.motion;
}

function formatNumber(value, options = {}) {
  if (value === null || value === undefined || value === "") return "--";
  const language = getLanguageOption();
  return new Intl.NumberFormat(language.locale, options).format(Number(value));
}

function formatMoney(value, currency = getCurrencyOption().code) {
  if (value === null || value === undefined || value === "") return "--";
  const language = getLanguageOption();
  try {
    return new Intl.NumberFormat(language.locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(Number(value));
  } catch {
    return `${currency} ${formatNumber(value, { maximumFractionDigits: 2 })}`;
  }
}

function formatDateTime(value) {
  if (!value) return "--";
  const language = getLanguageOption();
  return new Intl.DateTimeFormat(language.locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function moneyClass(value) {
  const number = Number(value || 0);
  if (number > 0) return "money-good";
  if (number < 0) return "money-bad";
  return "";
}

function setStatus(message, isError = false) {
  const bar = $("#health-strip");
  bar.textContent = message;
  bar.classList.toggle("bad", isError);
}

function setLiveStatus(isOnline, label) {
  $("#live-indicator").classList.toggle("online", isOnline);
  $("#live-label").textContent = label;
}

function populatePreferenceControls() {
  $("#language-selector").innerHTML = LANGUAGE_OPTIONS.map((item) => `<option value="${escapeHtml(item.code)}">${escapeHtml(item.label)} · ${escapeHtml(item.tier)}</option>`).join("");
  $("#currency-selector").innerHTML = CURRENCY_OPTIONS.map((item) => `<option value="${escapeHtml(item.code)}">${escapeHtml(item.code)} · ${escapeHtml(item.name)}</option>`).join("");
  $("#language-selector").value = state.preferences.language;
  $("#currency-selector").value = state.preferences.currency;
  $("#density-selector").value = state.preferences.density;
  $("#font-scale-selector").value = state.preferences.fontScale;
  $("#motion-selector").value = state.preferences.motion;
}

function applyStaticTranslations() {
  $$("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); });
  $$("[data-i18n-placeholder]").forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
}

function populatePreferenceControls() {
  $("#language-selector").innerHTML = LANGUAGE_OPTIONS.map((item) => `<option value="${escapeHtml(item.code)}">${escapeHtml(item.label)} • ${escapeHtml(item.tier)}</option>`).join("");
  $("#currency-selector").innerHTML = CURRENCY_OPTIONS.map((item) => `<option value="${escapeHtml(item.code)}">${escapeHtml(item.code)} • ${escapeHtml(item.name)}</option>`).join("");
  $("#language-selector").value = state.preferences.language;
  $("#currency-selector").value = state.preferences.currency;
  $("#density-selector").value = state.preferences.density;
  $("#font-scale-selector").value = state.preferences.fontScale;
  $("#motion-selector").value = state.preferences.motion;
}

function updateSummaryStrip() {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const language = getLanguageOption();
  $("#summary-environment").textContent = `ENV: ${state.dashboard?.signal_sources?.[0]?.environment || state.dashboard?.followers?.[0]?.environment || "TESTNET"}`;
  $("#summary-timezone").textContent = `TZ: ${timezone}`;
  $("#summary-display-currency").textContent = `${t("toolbar.currency")}: ${getCurrencyOption().code}`;
  $("#summary-language-tier").textContent = `${language.label} • ${language.tier}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function switchTab(tabId) {
  $$(".tab").forEach((button) => {
    const active = button.dataset.tab === tabId;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  $$(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${tabId}`));
}

function closeModal(selector) {
  $(selector).classList.add("hidden");
}

function openModal(selector) {
  $(selector).classList.remove("hidden");
}

function resetForm(form) {
  form.reset();
}

function formToJson(form) {
  const data = new FormData(form);
  const json = {};
  data.forEach((value, key) => {
    if (json[key] !== undefined) return;
    json[key] = value;
  });
  $$("input[type='checkbox'], input[type='radio']", form).forEach((input) => {
    if (input.type === "checkbox") {
      json[input.name] = input.checked;
    }
    if (input.type === "radio" && input.checked) {
      json[input.name] = input.value;
    }
  });
  Object.keys(json).forEach((key) => {
    if (json[key] === "") delete json[key];
  });
  return json;
}

function fillSelect(select, items, labelBuilder, valueKey = "id", emptyLabel = "") {
  const options = items.map((item) => `<option value="${escapeHtml(item[valueKey])}">${escapeHtml(labelBuilder(item))}</option>`);
  if (emptyLabel) options.unshift(`<option value="">${escapeHtml(emptyLabel)}</option>`);
  select.innerHTML = options.join("");
}

function renderMetrics() {
  const runtime = state.dashboard?.runtime_metrics || [];
  const performance = state.dashboard?.performance_metrics || [];
  $("#runtime-metrics").innerHTML = runtime.map((item) => renderMetricCard(item)).join("");
  $("#performance-metrics").innerHTML = performance.map((item) => renderMetricCard(item)).join("");
  const fx = state.dashboard?.fx_meta;
  $("#fx-strip").textContent = fx
    ? `${t("toolbar.currency")}: ${fx.display_currency} | FX ${fx.converted ? "converted" : "fallback"} | ${fx.conversion_source} | ${fx.updated_at ? formatDateTime(fx.updated_at) : "--"}`
    : "Display currency metadata unavailable";
}

function renderMetricCard(item) {
  const isMoney = /Value|PnL|Exposure/i.test(item.label);
  const display = isMoney && item.value !== "--"
    ? formatMoney(item.value, getCurrencyOption().code)
    : escapeHtml(item.value);
  return `
    <article class="metric-card" data-tone="${escapeHtml(item.tone || "neutral")}">
      <span class="metric-label">${escapeHtml(item.label)}</span>
      <strong class="metric-value ${isMoney ? moneyClass(item.value) : ""}">${display}</strong>
      <span class="metric-note">${escapeHtml(item.note || "")}</span>
    </article>
  `;
}

function renderSignalCards() {
  const items = state.dashboard?.signal_sources || [];
  $("#signal-cards").innerHTML = items.length ? items.map((source) => {
    const followers = source.follower_names || [];
    const followerPreview = followers.slice(0, 2).map((name) => `<span class="pill">${escapeHtml(name)}</span>`).join("");
    const overflow = followers.length > 2 ? `<span class="pill">+${followers.length - 2}</span>` : "";
    const dimmed = source.status !== "ACTIVE" || source.trading_ready_status === "FAILED";
    const readinessBadge = `<span class="badge ${source.status === "PAUSED" ? "paused" : source.trading_ready_status === "FAILED" ? "failed" : ""}">${escapeHtml(source.status)}</span>`;
    return `
      <article class="signal-card ${dimmed ? "is-dimmed" : ""}">
        <div class="signal-header">
          <div>
            <div class="signal-name">${escapeHtml(source.name)}</div>
            <div class="signal-meta-row">
              ${readinessBadge}
              <span class="pill">${escapeHtml(source.default_copy_mode)}</span>
              ${source.broadcast_trade_enabled ? `<span class="pill">BROADCAST</span>` : `<span class="pill">DIRECT</span>`}
              <span class="pill">${escapeHtml(source.exchange)}</span>
            </div>
          </div>
          <div class="signal-meta-row">
            <span class="readiness-chip ${escapeHtml(source.trading_ready_status)}">${escapeHtml(source.trading_ready_status)}</span>
          </div>
        </div>
        <div class="signal-stats">
          <div class="signal-stat"><div class="metric-label">${escapeHtml(t("table.pairs"))}</div><div class="signal-stat-value">${escapeHtml(source.pairs_scope || "ALL")}</div></div>
          <div class="signal-stat"><div class="metric-label">${escapeHtml(t("metrics.followers"))}</div><div class="signal-stat-value">${formatNumber(source.follower_count || 0, { maximumFractionDigits: 0 })}</div></div>
          <div class="signal-stat"><div class="metric-label">${escapeHtml(t("table.mode"))}</div><div class="signal-stat-value">${escapeHtml(source.default_copy_mode)}</div></div>
          <div class="signal-stat"><div class="metric-label">${escapeHtml(t("table.leverage"))}</div><div class="signal-stat-value">${escapeHtml(source.default_leverage ?? "AUTO")}</div></div>
        </div>
        <div class="signal-followers">${followerPreview || `<span class="pill">${escapeHtml(t("metrics.followers"))}: 0</span>`}${overflow}</div>
        <div class="signal-actions">
          <button type="button" class="primary primary-inline signal-open-builder" data-id="${source.id}" data-exchange="${source.exchange}">Build</button>
          <button type="button" class="secondary signal-edit" data-id="${source.id}">${escapeHtml(t("actions.edit"))}</button>
          <button type="button" class="secondary signal-validate" data-id="${source.id}">${escapeHtml(t("actions.validate"))}</button>
        </div>
      </article>
    `;
  }).join("") : `<article class="signal-card"><div class="drawer-empty">No signal sources yet.</div></article>`;
}

function renderReadinessBadges(item) {
  const statuses = [
    ["Credential", item.credential_status],
    ["Permission", item.permission_status],
    ["Connectivity", item.connectivity_status],
    ["Trading", item.trading_ready_status],
  ];
  return statuses.map(([label, statusValue]) => `<span class="readiness-chip ${escapeHtml(statusValue)}">${escapeHtml(label)} · ${escapeHtml(statusValue)}</span>`).join("");
}

function renderManageSignalsTable() {
  $("#manage-signals-table").innerHTML = (state.dashboard?.signal_sources || []).map((source) => `
    <tr data-id="${source.id}">
      <td>${escapeHtml(source.name)}</td>
      <td>${escapeHtml(source.exchange)}</td>
      <td>${escapeHtml(source.pairs_scope)}</td>
      <td>
        <div class="detail-value">${renderReadinessBadges(source)}</div>
      </td>
      <td>
        <div class="header-actions">
          <button type="button" class="secondary signal-edit" data-id="${source.id}">Edit</button>
          <button type="button" class="secondary signal-validate" data-id="${source.id}">Validate</button>
          <button type="button" class="danger signal-delete-row" data-id="${source.id}">Delete</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderFollowersTable() {
  $("#followers-table").innerHTML = (state.dashboard?.followers || []).map((item) => `
    <tr data-id="${item.id}">
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.exchange)}</td>
      <td><div class="detail-value">${renderReadinessBadges(item)}</div></td>
      <td>
        <div>${escapeHtml(item.validation_status)}</div>
        <div class="rail-label">${escapeHtml(item.validation_message || item.validation_reasons?.[0] || "--")}</div>
      </td>
      <td>
        <div class="header-actions">
          <button type="button" class="secondary follower-edit" data-id="${item.id}">${escapeHtml(t("actions.edit"))}</button>
          <button type="button" class="secondary follower-validate" data-id="${item.id}">${escapeHtml(t("actions.validate"))}</button>
          <button type="button" class="secondary follower-toggle" data-id="${item.id}" data-status="${item.status}">${item.status === "ACTIVE" ? escapeHtml(t("actions.pause")) : escapeHtml(t("actions.resume"))}</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function renderCopyTradesTable() {
  $("#copy-trades-table").innerHTML = (state.dashboard?.copy_trades || []).map((item) => `
    <tr data-id="${item.id}" class="${state.currentCopyTradeId === item.id ? "is-active" : ""}">
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.signal_name)}<div class="rail-label">${escapeHtml(item.follower_name)}</div></td>
      <td><span class="pill">${escapeHtml(item.copy_mode)}</span></td>
      <td><span class="badge ${item.status !== "ACTIVE" ? "paused" : ""}">${escapeHtml(item.status)}</span></td>
      <td>
        <div class="detail-value">${escapeHtml(item.validation_message || item.validation_status)}</div>
        ${(item.validation_reasons || []).slice(0, 2).map((reason) => `<div class="rail-label">${escapeHtml(reason)}</div>`).join("")}
      </td>
      <td>
        <div class="header-actions">
          <button type="button" class="secondary copytrade-edit" data-id="${item.id}">${escapeHtml(t("actions.edit"))}</button>
          <button type="button" class="danger copytrade-delete-row" data-id="${item.id}">${escapeHtml(t("actions.delete"))}</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function syncCopyTradeSelects() {
  fillSelect($("#copytrade-editor-signal"), state.dashboard?.signal_sources || [], (item) => item.name);
  fillSelect($("#copytrade-editor-follower"), state.dashboard?.followers || [], (item) => `${item.name} | ${item.exchange}`);
}

function updateCopyTradeModeUI() {
  const form = $("#copytrade-form");
  const mode = form.copy_mode.value;
  $("#scale-factor-row").classList.toggle("hidden", mode !== "SCALE");
  $$(".mode-card").forEach((card) => {
    const input = card.querySelector("input");
    card.classList.toggle("is-selected", input.checked);
  });
}

function updateCopyTradeTemplatePreview() {
  const value = $("#copytrade-form").command_template.value.trim();
  $("#copytrade-command-preview").textContent = value ? value.slice(0, 160) : "No command template saved.";
}

function openCopyTradeEditor(copyTradeId = null) {
  const form = $("#copytrade-form");
  $("#copytrade-empty").classList.add("hidden");
  form.classList.remove("hidden");
  resetForm(form);
  form.copy_trade_id.value = "";
  state.currentCopyTradeId = copyTradeId;
  syncCopyTradeSelects();
  if (!copyTradeId) {
    $("#copytrade-editor-title").textContent = t("actions.addCopyTrade");
    $("#copytrade-delete").classList.add("hidden");
    $("#copytrade-enabled").checked = true;
    form.copy_mode.value = "EXACT";
    form.scale_factor.value = "1";
    $("#copytrade-validation-strip").textContent = "No validation yet.";
    updateCopyTradeModeUI();
    updateCopyTradeTemplatePreview();
    return;
  }
  const item = state.dashboard.copy_trades.find((copyTrade) => copyTrade.id === copyTradeId);
  if (!item) return;
  $("#copytrade-editor-title").textContent = `${t("actions.save")} | ${item.name}`;
  $("#copytrade-delete").classList.remove("hidden");
  form.copy_trade_id.value = item.id;
  form.name.value = item.name;
  form.signal_source_id.value = item.signal_source_id;
  form.follower_account_id.value = item.follower_account_id;
  form.copy_mode.value = item.copy_mode;
  form.scale_factor.value = item.scale_factor;
  form.override_leverage.value = item.override_leverage || "";
  form.command_template.value = item.command_template || "";
  form.notes.value = item.notes || "";
  $("#copytrade-enabled").checked = !!item.enabled;
  $("#copytrade-validation-strip").innerHTML = renderReadinessBadges({
    credential_status: item.validation_status,
    permission_status: item.validation_status,
    connectivity_status: item.validation_status,
    trading_ready_status: item.validation_status,
  }) + (item.validation_reasons || []).map((reason) => `<div class="rail-label">${escapeHtml(reason)}</div>`).join("");
  updateCopyTradeModeUI();
  updateCopyTradeTemplatePreview();
}

function closeCopyTradeEditor() {
  state.currentCopyTradeId = null;
  $("#copytrade-form").classList.add("hidden");
  $("#copytrade-empty").classList.remove("hidden");
}

function openSignalModal(signalId = null) {
  const form = $("#signal-form");
  resetForm(form);
  form.signal_source_id.value = "";
  state.currentSignalId = signalId;
  if (!signalId) {
    $("#signal-modal-title").textContent = "Create Signal";
    $("#signal-delete").classList.add("hidden");
    openModal("#signal-modal");
    return;
  }
  const signal = state.dashboard.signal_sources.find((item) => item.id === signalId);
  if (!signal) return;
  $("#signal-modal-title").textContent = `Edit Signal | ${signal.name}`;
  $("#signal-delete").classList.remove("hidden");
  form.signal_source_id.value = signal.id;
  form.name.value = signal.name;
  form.exchange.value = signal.exchange;
  form.environment.value = signal.environment;
  form.source_account.value = signal.source_account;
  form.pairs_scope.value = signal.pairs_scope;
  form.default_copy_mode.value = signal.default_copy_mode;
  form.default_scale_factor.value = signal.default_scale_factor;
  form.default_leverage.value = signal.default_leverage || "";
  form.margin_mode.value = signal.margin_mode;
  form.hedge_mode.checked = !!signal.hedge_mode;
  form.broadcast_trade_enabled.checked = !!signal.broadcast_trade_enabled;
  form.description.value = signal.description || "";
  openModal("#signal-modal");
}

function openFollowerModal(followerId = null) {
  const form = $("#follower-form");
  resetForm(form);
  form.follower_id.value = "";
  if (!followerId) {
    $("#follower-modal-title").textContent = "Create API Account";
    $("#follower-delete").classList.add("hidden");
    openModal("#follower-modal");
    return;
  }
  const follower = state.dashboard.followers.find((item) => item.id === followerId);
  if (!follower) return;
  $("#follower-modal-title").textContent = `Edit API Account | ${follower.name}`;
  $("#follower-delete").classList.remove("hidden");
  form.follower_id.value = follower.id;
  form.name.value = follower.name;
  form.exchange.value = follower.exchange;
  form.environment.value = follower.environment;
  form.leverage.value = follower.leverage || "";
  form.margin_mode.value = follower.margin_mode;
  form.hedge_mode.checked = !!follower.hedge_mode;
  openModal("#follower-modal");
}

function renderPresets() {
  $("#presets-table").innerHTML = (state.dashboard?.command_presets || []).map((item) => `
    <tr>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.exchange)}</td>
      <td>${escapeHtml(item.environment)}</td>
      <td>${escapeHtml(item.signal_source_id || "--")}</td>
      <td>${formatDateTime(item.created_at)}</td>
    </tr>
  `).join("");
}

function renderExecutionRows(executions) {
  $("#live-executions-table").innerHTML = executions.length ? executions.map((item) => `
    <tr data-task-id="${item.id}" tabindex="0">
      <td>${escapeHtml(item.signal_name || item.signal_id.slice(0, 8))}</td>
      <td>${escapeHtml(item.follower_name || item.follower_account_id.slice(0, 8))}</td>
      <td>${escapeHtml(item.symbol)}</td>
      <td>${escapeHtml(item.action)}</td>
      <td><span class="severity-chip ${escapeHtml(item.exchange_stage || item.status)}">${escapeHtml(item.exchange_stage || item.status)}</span></td>
      <td>${escapeHtml(item.queue_name)}</td>
      <td>${item.queue_latency_ms ? `${formatNumber(item.queue_latency_ms, { maximumFractionDigits: 0 })} ms` : "--"}</td>
    </tr>
  `).join("") : `<tr><td colspan="7">No execution tasks yet.</td></tr>`;
}

function renderQuickLogFilters() {
  $("#log-quick-filters").innerHTML = QUICK_LOG_TYPES.map((type) => {
    const active = (type === "ALL" && !state.logs.log_type) || state.logs.log_type === type;
    return `<button type="button" class="quick-pill ${active ? "is-active" : ""}" data-log-quick="${type}">${escapeHtml(type)}</button>`;
  }).join("");
}

function renderLogs(response) {
  state.logsPage = response;
  renderQuickLogFilters();
  $("#logs-table").innerHTML = response.items.map((item) => `
    <tr data-log-id="${item.id}" tabindex="0">
      <td>${formatDateTime(item.timestamp)}</td>
      <td>${escapeHtml(item.exchange)}</td>
      <td><span class="severity-chip ${escapeHtml(item.log_type)}">${escapeHtml(item.log_type)}</span></td>
      <td>${escapeHtml(item.log_key)}</td>
      <td class="${moneyClass(item.pnl)}">${item.pnl !== null ? formatMoney(item.pnl, getCurrencyOption().code) : "--"}</td>
      <td>${escapeHtml(item.message)}</td>
    </tr>
  `).join("");
  $("#logs-summary").textContent = `${formatNumber(response.total, { maximumFractionDigits: 0 })} records | page ${response.page}/${response.page_count}`;
  renderLogPagination(response.page, response.page_count);
  if (response.items[0] && !state.currentLogId) {
    renderLogDetail(response.items[0]);
  }
}

function renderLogPagination(currentPage, pageCount) {
  const buttons = [];
  buttons.push(`<button type="button" class="page-number ${currentPage === 1 ? "is-disabled" : ""}" data-page="${Math.max(1, currentPage - 1)}">Prev</button>`);
  for (let page = Math.max(1, currentPage - 2); page <= Math.min(pageCount, currentPage + 2); page += 1) {
    buttons.push(`<button type="button" class="page-number ${page === currentPage ? "is-active" : ""}" data-page="${page}">${page}</button>`);
  }
  buttons.push(`<button type="button" class="page-number ${currentPage === pageCount ? "is-disabled" : ""}" data-page="${Math.min(pageCount, currentPage + 1)}">Next</button>`);
  $("#log-pages").innerHTML = buttons.join("");
}

function renderLogDetail(item) {
  state.currentLogId = item.id;
  $("#log-detail-empty").classList.add("hidden");
  $("#log-detail-content").classList.remove("hidden");
  const metadata = [
    ["Type", item.log_type],
    ["Exchange", item.exchange],
    ["Key", item.log_key],
    ["Task", item.linked_task_id || "--"],
    ["Signal", item.linked_signal_id || "--"],
    ["Follower", item.linked_follower_name || item.linked_follower_id || "--"],
    ["Timestamp", formatDateTime(item.timestamp)],
    ["PnL", item.pnl !== null ? formatMoney(item.pnl) : "--"],
  ];
  $("#log-detail-meta").innerHTML = metadata.map(([key, value]) => `
    <div class="detail-item">
      <div class="detail-key">${escapeHtml(key)}</div>
      <div class="detail-value">${escapeHtml(value)}</div>
    </div>
  `).join("");
  $("#log-detail-json").textContent = JSON.stringify({
    message: item.message,
    details: item.details || {},
    exchange_response: item.exchange_response || null,
  }, null, 2);
}

function renderPositions() {
  const summary = state.dashboard?.equity_summary || {};
  const cards = [
    ["Total Notional", summary.total_notional || 0, ""],
    ["Long Exposure", summary.long_exposure || 0, ""],
    ["Short Exposure", summary.short_exposure || 0, ""],
    ["Stale Snapshots", summary.stale_snapshots || 0, ""],
  ];
  $("#equity-summary-grid").innerHTML = cards.map(([label, value]) => renderMetricCard({
    label,
    value,
    tone: label === "Stale Snapshots" && Number(value) > 0 ? "warning" : "neutral",
    note: label === "Stale Snapshots" ? "snapshot freshness" : `display ${getCurrencyOption().code}`,
  })).join("");

  $("#positions-table").innerHTML = state.positions.length ? state.positions.map((item) => `
    <tr>
      <td>${escapeHtml(item.symbol)}<div class="rail-label">${escapeHtml(item.follower_name || item.source)}</div></td>
      <td>${escapeHtml(item.exchange)}<div class="rail-label">${escapeHtml(item.margin_mode || "--")}</div></td>
      <td>${item.display_value !== null ? formatMoney(item.display_value, getCurrencyOption().code) : formatMoney(item.notional_exposure || 0, getCurrencyOption().code)}</td>
      <td>${formatNumber(item.entry_price || 0, { maximumFractionDigits: 8 })}</td>
      <td class="${moneyClass(item.unrealized_pnl)}">${item.unrealized_pnl !== null ? formatMoney(item.unrealized_pnl, getCurrencyOption().code) : "--"}</td>
      <td>${escapeHtml(item.leverage ?? "--")}</td>
      <td><span class="severity-chip ${item.freshness === "stale" ? "WARNING" : item.freshness === "aging" ? "INFO" : "EXECUTION"}">${escapeHtml(item.freshness)}</span></td>
      <td>${formatDateTime(item.captured_at)}</td>
    </tr>
  `).join("") : `<tr><td colspan="8">No position snapshots yet.</td></tr>`;
}

async function openAuditDrawer(taskId) {
  state.currentAuditTaskId = taskId;
  const audit = await api(`/v1/executions/${taskId}/audit`);
  $("#audit-drawer-title").textContent = `${audit.task.symbol} | ${audit.task.follower_name || audit.task.follower_account_id}`;
  $("#audit-summary").innerHTML = [
    ["Signal", audit.task.signal_name || audit.task.signal_id],
    ["Action", audit.task.action],
    ["Status", audit.task.status],
    ["Exchange Stage", audit.task.exchange_stage || audit.task.status],
    ["Queue", audit.task.queue_name],
    ["Latency", audit.task.queue_latency_ms ? `${audit.task.queue_latency_ms} ms` : "--"],
  ].map(([key, value]) => `<div class="detail-item"><div class="detail-key">${escapeHtml(key)}</div><div class="detail-value">${escapeHtml(value)}</div></div>`).join("");
  $("#audit-timeline").innerHTML = audit.timeline.map((item) => `
    <div class="timeline-item" data-level="${escapeHtml(item.level)}">
      <div class="timeline-meta"><span>${escapeHtml(item.title)}</span><span>${formatDateTime(item.timestamp)}</span></div>
      <div>${escapeHtml(item.message)}</div>
    </div>
  `).join("");
  $("#audit-related-logs").innerHTML = audit.related_logs.map((item) => `
    <div class="inline-list-item">
      <div class="timeline-meta"><span class="severity-chip ${escapeHtml(item.log_type)}">${escapeHtml(item.log_type)}</span><span>${formatDateTime(item.timestamp)}</span></div>
      <div>${escapeHtml(item.message)}</div>
    </div>
  `).join("");
  $("#audit-drawer").classList.remove("hidden");
}

function closeAuditDrawer() {
  $("#audit-drawer").classList.add("hidden");
}

function updateBuilderLinks(exchange) {
  const meta = EXCHANGE_META[exchange] || EXCHANGE_META.BINANCE;
  $("#builder-title").textContent = meta.title;
  $("#builder-link-api").href = meta.api;
  $("#builder-link-guide").href = meta.guide;
  $("#builder-link-register").href = meta.register;
  $("#builder-product-tabs").innerHTML = meta.products.map((product, index) => `
    <button type="button" class="product-tab ${index === 0 ? "is-active" : ""}" data-product="${escapeHtml(product.value)}">${escapeHtml(product.label)}</button>
  `).join("");
  $("#builder-product-type").value = meta.products[0].value;
  $("#builder-balance").textContent = `Connected environment: ${$("#builder-environment").value} | ${exchange}`;
}

async function ensureInstruments(exchange) {
  if (state.instruments[exchange].length) return;
  const instruments = await api(`/v1/instruments?exchange=${exchange}`);
  state.instruments[exchange] = instruments.map((item) => item.symbol || item.symbolName || item.instId).filter(Boolean);
}

async function syncBuilderReferences() {
  const exchange = $("#builder-exchange").value;
  updateBuilderLinks(exchange);
  const accounts = (state.dashboard?.followers || []).filter((item) => item.exchange === exchange);
  fillSelect($("#builder-account"), accounts, (item) => `${item.name} | ${item.exchange}`, "id", "--");
  await ensureInstruments(exchange);
  fillSelect($("#builder-symbol"), state.instruments[exchange].map((symbol) => ({ id: symbol, symbol })), (item) => item.symbol, "id");
}

function updateBuilderActionPanels() {
  const action = $("#builder-action-input").value;
  const captions = {
    BUY: "BUY route: build an opening or add-position command for the selected exchange account.",
    SELL: "SELL route: build a short entry, trim, or reversal command with the same execution controls.",
    CANCEL_ORDERS: "Cancel Orders route: clear working orders only, without changing the position unless you explicitly combine actions.",
    CLOSE_POSITION: "Close Position route: flatten the whole position or target long and short legs separately.",
  };
  $("#builder-action-caption").textContent = captions[action];
  $("#trade-entry-panel").classList.toggle("hidden", action === "CANCEL_ORDERS");
  $("#cancel-orders-panel").classList.toggle("hidden", action !== "CANCEL_ORDERS");
  $("#close-position-panel").classList.toggle("hidden", action !== "CLOSE_POSITION");
}

function renderBuilderActionSegments() {
  const action = $("#builder-action-input").value;
  $$(".segment").forEach((button) => button.classList.toggle("is-active", button.dataset.value === action));
  updateBuilderActionPanels();
}

function addTakeProfitStep(data = {}) {
  const row = document.createElement("div");
  row.className = "form-grid two-col";
  row.innerHTML = `
    <input data-field="amount" placeholder="Amount %" value="${escapeHtml(data.amount || "")}" />
    <div class="search-shell">
      <input data-field="percent" placeholder="Take Profit %" value="${escapeHtml(data.takeProfitPercent || "")}" />
      <button type="button" class="danger remove-tp-step">Delete</button>
    </div>
  `;
  $("#tp-steps").appendChild(row);
}

function collectTakeProfitSteps() {
  return $$("#tp-steps .form-grid").map((row, index) => ({
    id: String(index + 1),
    amount: row.querySelector('[data-field="amount"]').value || "",
    takeProfitPercent: row.querySelector('[data-field="percent"]').value || "",
  })).filter((item) => item.amount || item.takeProfitPercent);
}

function builderPayloadFromForm() {
  const payload = formToJson($("#builder-form"));
  payload.name = payload.name || `Studio-${Date.now()}`;
  payload.take_profit_steps = collectTakeProfitSteps();
  return payload;
}

function renderBuilderPreview() {
  const payload = builderPayloadFromForm();
  $("#command-output").value = JSON.stringify(payload, null, 2);
  setStatus("Builder preview generated.");
}

async function saveBuilderPreset(execute = false) {
  const payload = builderPayloadFromForm();
  if (execute) {
    const result = await api("/v1/commands/execute", { method: "POST", body: JSON.stringify(payload) });
    state.lastExecutionResponse = result;
    $("#execution-output").value = JSON.stringify(result, null, 2);
    setStatus(result.accepted ? "Execution accepted." : "Execution failed.", !result.accepted);
  } else {
    const result = await api("/v1/commands/generate", { method: "POST", body: JSON.stringify(payload) });
    $("#command-output").value = result.raw_command;
    setStatus("Builder preset saved.");
  }
  await refreshDashboard();
}

function renderBuilderFromSignal(signalId, exchange) {
  switchTab("builder");
  $("#builder-exchange").value = exchange;
  const builderForm = $("#builder-form");
  if (builderForm.signal_source_id) {
    builderForm.signal_source_id.value = signalId;
  }
  syncBuilderReferences().catch((error) => setStatus(error.message, true));
}

function renderWorkspaceSearch() {
  const query = $("#workspace-search").value.trim().toLowerCase();
  if (!query) return;
  const signal = (state.dashboard?.signal_sources || []).find((item) => `${item.name} ${item.source_account}`.toLowerCase().includes(query));
  if (signal) {
    switchTab("signals");
    return;
  }
  const copyTrade = (state.dashboard?.copy_trades || []).find((item) => `${item.name} ${item.follower_name} ${item.signal_name}`.toLowerCase().includes(query));
  if (copyTrade) {
    switchTab("copy-trades");
    openCopyTradeEditor(copyTrade.id);
    return;
  }
  const follower = (state.dashboard?.followers || []).find((item) => `${item.name} ${item.exchange}`.toLowerCase().includes(query));
  if (follower) {
    switchTab("manage-signals");
    return;
  }
  const log = (state.logsPage?.items || []).find((item) => `${item.message} ${item.log_key}`.toLowerCase().includes(query));
  if (log) {
    switchTab("logs");
    renderLogDetail(log);
    return;
  }
  setStatus("No matching signal, account, symbol, or log entry.", true);
}

async function refreshDashboard() {
  state.dashboard = await api(`/v1/dashboard?display_currency=${encodeURIComponent(getCurrencyOption().code)}`);
  renderMetrics();
  renderSignalCards();
  renderManageSignalsTable();
  renderFollowersTable();
  renderCopyTradesTable();
  renderPresets();
  renderExecutionRows(state.liveSnapshot?.executions || state.dashboard.recent_executions || []);
  updateSummaryStrip();
  syncCopyTradeSelects();
  await syncBuilderReferences();
  if (state.currentCopyTradeId) openCopyTradeEditor(state.currentCopyTradeId);
}

async function refreshPositions() {
  state.positions = await api(`/v1/positions?display_currency=${encodeURIComponent(getCurrencyOption().code)}`);
  renderPositions();
}

async function refreshLogs() {
  const params = new URLSearchParams({
    page: String(state.logs.page),
    limit: String(state.logs.limit),
    sort_by: state.logs.sort_by,
    sort_order: state.logs.sort_order,
  });
  if (state.logs.exchange) params.set("exchange", state.logs.exchange);
  if (state.logs.log_type) params.set("log_type", state.logs.log_type);
  if (state.logs.search) params.set("search", state.logs.search);
  if (state.logs.linked_task_id) params.set("linked_task_id", state.logs.linked_task_id);
  renderLogs(await api(`/v1/logs/query?${params.toString()}`));
}

async function refreshHealth() {
  const data = await api("/v1/health/exchanges");
  const summary = data.checks.map((item) => `${item.name}:${item.ok ? "OK" : "DOWN"}`).join(" | ");
  setStatus(`TradeNodeX ready | ${summary}`);
}

function connectLiveStream() {
  if (state.liveSocket) state.liveSocket.close();
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/v1/ws/stream`);
  state.liveSocket = socket;

  socket.addEventListener("open", () => {
    setLiveStatus(true, "Realtime stream connected");
    if (state.liveHeartbeat) clearInterval(state.liveHeartbeat);
    state.liveHeartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 5000);
  });

  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type !== "snapshot") return;
    state.liveSnapshot = payload;
    setLiveStatus(true, `Realtime stream connected | ${payload.counts.logs} live logs`);
    renderExecutionRows(payload.executions || []);
    $("#execution-feed-status").textContent = `${payload.executions?.length || 0} execution rows loaded`;
    if (state.logs.page === 1 && !state.logs.exchange && !state.logs.log_type && !state.logs.search && !state.logs.linked_task_id) {
      renderLogs({
        items: payload.logs || [],
        total: payload.counts.logs || 0,
        page: 1,
        limit: state.logs.limit,
        page_count: Math.max(1, Math.ceil((payload.counts.logs || 0) / state.logs.limit)),
      });
    }
  });

  socket.addEventListener("close", () => {
    setLiveStatus(false, "Realtime stream offline | reconnecting...");
    window.setTimeout(connectLiveStream, 3000);
  });

  socket.addEventListener("error", () => setLiveStatus(false, "Realtime stream error"));
}

function bindTabs() {
  $$(".tab").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
}

function bindPreferences() {
  $("#language-selector").addEventListener("change", (event) => {
    state.preferences.language = event.target.value;
    persistPreferences();
    renderAll();
  });
  $("#currency-selector").addEventListener("change", async (event) => {
    state.preferences.currency = event.target.value;
    persistPreferences();
    await refreshDashboard();
    await refreshPositions();
    renderAll(false);
  });
  $("#density-selector").addEventListener("change", (event) => {
    state.preferences.density = event.target.value;
    persistPreferences();
    applyDocumentPreferences();
  });
  $("#font-scale-selector").addEventListener("change", (event) => {
    state.preferences.fontScale = event.target.value;
    persistPreferences();
    applyDocumentPreferences();
  });
  $("#motion-selector").addEventListener("change", (event) => {
    state.preferences.motion = event.target.value;
    persistPreferences();
    applyDocumentPreferences();
  });
}

function renderAll(repaintData = true) {
  applyDocumentPreferences();
  populatePreferenceControls();
  applyStaticTranslations();
  updateSummaryStrip();
  renderQuickLogFilters();
  if (!repaintData) return;
  if (state.dashboard) {
    renderMetrics();
    renderSignalCards();
    renderManageSignalsTable();
    renderFollowersTable();
    renderCopyTradesTable();
    renderPresets();
    renderExecutionRows(state.liveSnapshot?.executions || state.dashboard.recent_executions || []);
    if (state.currentCopyTradeId) openCopyTradeEditor(state.currentCopyTradeId);
  }
  if (state.positions.length) renderPositions();
  if (state.logsPage) renderLogs(state.logsPage);
}

function bindStaticActions() {
  $("#workspace-search-action").addEventListener("click", renderWorkspaceSearch);
  $("#workspace-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      renderWorkspaceSearch();
    }
  });

  $("#refresh-dashboard").addEventListener("click", async () => {
    await refreshDashboard();
    await refreshLogs();
    await refreshPositions();
  });
  $("#refresh-copytrades").addEventListener("click", refreshDashboard);
  $("#refresh-followers").addEventListener("click", refreshDashboard);
  $("#refresh-presets").addEventListener("click", refreshDashboard);
  $("#refresh-logs").addEventListener("click", refreshLogs);
  $("#refresh-positions").addEventListener("click", refreshPositions);
  $("#open-create-signal").addEventListener("click", () => openSignalModal());
  $("#open-create-signal-secondary").addEventListener("click", () => openSignalModal());
  $("#open-create-follower").addEventListener("click", () => openFollowerModal());
  $("#open-create-copytrade").addEventListener("click", () => {
    switchTab("copy-trades");
    openCopyTradeEditor();
  });

  $("#close-signal-modal").addEventListener("click", () => closeModal("#signal-modal"));
  $("#close-follower-modal").addEventListener("click", () => closeModal("#follower-modal"));
  $("#close-audit-drawer").addEventListener("click", closeAuditDrawer);
  $("#copytrade-cancel").addEventListener("click", closeCopyTradeEditor);
  $("#toggle-command-template").addEventListener("click", () => $("#copytrade-command-wrap").classList.toggle("hidden"));
  $("#copytrade-form").copy_mode && ($$("#copy-mode-cards input").forEach((input) => input.addEventListener("change", updateCopyTradeModeUI)));
  $("#copytrade-form").command_template.addEventListener("input", updateCopyTradeTemplatePreview);

  $("#builder-exchange").addEventListener("change", syncBuilderReferences);
  $("#builder-environment").addEventListener("change", () => updateBuilderLinks($("#builder-exchange").value));
  $("#generate-command").addEventListener("click", renderBuilderPreview);
  $("#copy-command").addEventListener("click", async () => {
    const content = $("#command-output").value.trim();
    if (!content) {
      setStatus("Nothing to copy yet.", true);
      return;
    }
    await navigator.clipboard.writeText(content);
    setStatus("Command copied to clipboard.");
  });
  $("#save-command").addEventListener("click", () => saveBuilderPreset(false).catch((error) => setStatus(error.message, true)));
  $("#execute-command").addEventListener("click", () => saveBuilderPreset(true).catch((error) => setStatus(error.message, true)));
  $("#add-tp-step").addEventListener("click", () => addTakeProfitStep());
  $("#apply-log-filter").addEventListener("click", async () => {
    state.logs.page = 1;
    state.logs.exchange = $("#log-exchange-filter").value;
    state.logs.log_type = $("#log-type-filter").value;
    state.logs.search = $("#log-search").value.trim();
    state.logs.sort_by = $("#log-sort-by").value;
    state.logs.sort_order = $("#log-sort-order").value;
    state.logs.linked_task_id = "";
    await refreshLogs();
  });
  $("#jump-latest-logs").addEventListener("click", async () => {
    state.logs.page = 1;
    await refreshLogs();
  });

  $("#signal-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formToJson(event.currentTarget);
    const id = payload.signal_source_id;
    delete payload.signal_source_id;
    await api(id ? `/v1/signal-sources/${id}` : "/v1/signal-sources", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
    closeModal("#signal-modal");
    await refreshDashboard();
  });
  $("#signal-validate").addEventListener("click", async () => {
    const id = $("#signal-form").signal_source_id.value;
    if (!id) {
      setStatus("Save the signal before validating.", true);
      return;
    }
    const result = await api(`/v1/signal-sources/${id}/validate`, { method: "POST" });
    setStatus(result.ok ? "Signal source validation passed." : `Signal source validation failed: ${result.message || "unknown error"}`, !result.ok);
    await refreshDashboard();
  });
  $("#signal-delete").addEventListener("click", async () => {
    const id = $("#signal-form").signal_source_id.value;
    if (!id || !window.confirm("Delete this signal source and attached copy trades?")) return;
    await api(`/v1/signal-sources/${id}`, { method: "DELETE" });
    closeModal("#signal-modal");
    await refreshDashboard();
  });

  $("#follower-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formToJson(event.currentTarget);
    const id = payload.follower_id;
    delete payload.follower_id;
    payload.exact_copy_mode = true;
    await api(id ? `/v1/followers/${id}` : "/v1/followers", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
    closeModal("#follower-modal");
    await refreshDashboard();
  });
  $("#follower-delete").addEventListener("click", async () => {
    const id = $("#follower-form").follower_id.value;
    if (!id || !window.confirm("Delete this API account?")) return;
    await api(`/v1/followers/${id}`, { method: "DELETE" });
    closeModal("#follower-modal");
    await refreshDashboard();
  });

  $("#copytrade-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = formToJson(event.currentTarget);
    const id = payload.copy_trade_id;
    delete payload.copy_trade_id;
    await api(id ? `/v1/copy-trades/${id}` : "/v1/copy-trades", { method: id ? "PATCH" : "POST", body: JSON.stringify(payload) });
    await refreshDashboard();
  });
  $("#copytrade-delete").addEventListener("click", async () => {
    if (!state.currentCopyTradeId || !window.confirm("Delete this copy trade?")) return;
    await api(`/v1/copy-trades/${state.currentCopyTradeId}`, { method: "DELETE" });
    closeCopyTradeEditor();
    await refreshDashboard();
  });

  document.addEventListener("click", async (event) => {
    const segment = event.target.closest(".segment");
    if (segment) {
      $("#builder-action-input").value = segment.dataset.value;
      renderBuilderActionSegments();
      return;
    }
    const productTab = event.target.closest(".product-tab");
    if (productTab) {
      $$(".product-tab").forEach((button) => button.classList.toggle("is-active", button === productTab));
      $("#builder-product-type").value = productTab.dataset.product;
      return;
    }
    const signalEdit = event.target.closest(".signal-edit");
    if (signalEdit) return openSignalModal(signalEdit.dataset.id);
    const signalValidate = event.target.closest(".signal-validate");
    if (signalValidate) {
      const result = await api(`/v1/signal-sources/${signalValidate.dataset.id}/validate`, { method: "POST" });
      setStatus(result.ok ? "Signal source validation passed." : `Signal source validation failed: ${result.message || "unknown error"}`, !result.ok);
      await refreshDashboard();
      return;
    }
    const signalDelete = event.target.closest(".signal-delete-row");
    if (signalDelete) {
      if (!window.confirm("Delete this signal source and attached copy trades?")) return;
      await api(`/v1/signal-sources/${signalDelete.dataset.id}`, { method: "DELETE" });
      await refreshDashboard();
      return;
    }
    const signalOpenBuilder = event.target.closest(".signal-open-builder");
    if (signalOpenBuilder) {
      renderBuilderFromSignal(signalOpenBuilder.dataset.id, signalOpenBuilder.dataset.exchange);
      return;
    }
    const followerEdit = event.target.closest(".follower-edit");
    if (followerEdit) return openFollowerModal(followerEdit.dataset.id);
    const followerValidate = event.target.closest(".follower-validate");
    if (followerValidate) {
      await api(`/v1/followers/${followerValidate.dataset.id}/validate`, { method: "POST" });
      await refreshDashboard();
      return;
    }
    const followerToggle = event.target.closest(".follower-toggle");
    if (followerToggle) {
      const action = followerToggle.dataset.status === "ACTIVE" ? "pause" : "resume";
      await api(`/v1/followers/${followerToggle.dataset.id}/${action}`, { method: "POST" });
      await refreshDashboard();
      return;
    }
    const copyTradeEdit = event.target.closest(".copytrade-edit") || event.target.closest("#copy-trades-table tbody tr");
    if (copyTradeEdit?.dataset?.id) {
      openCopyTradeEditor(copyTradeEdit.dataset.id);
      return;
    }
    const copyTradeDelete = event.target.closest(".copytrade-delete-row");
    if (copyTradeDelete) {
      if (!window.confirm("Delete this copy trade?")) return;
      await api(`/v1/copy-trades/${copyTradeDelete.dataset.id}`, { method: "DELETE" });
      await refreshDashboard();
      return;
    }
    const logRow = event.target.closest("#logs-table tr");
    if (logRow?.dataset?.logId) {
      const log = state.logsPage?.items?.find((item) => item.id === logRow.dataset.logId);
      if (log) renderLogDetail(log);
      return;
    }
    const quickPill = event.target.closest("[data-log-quick]");
    if (quickPill) {
      state.logs.log_type = quickPill.dataset.logQuick === "ALL" ? "" : quickPill.dataset.logQuick;
      $("#log-type-filter").value = state.logs.log_type;
      state.logs.page = 1;
      await refreshLogs();
      return;
    }
    const pageSize = event.target.closest(".page-size");
    if (pageSize) {
      state.logs.limit = Number(pageSize.dataset.limit);
      state.logs.page = 1;
      $$(".page-size").forEach((button) => button.classList.toggle("is-active", button === pageSize));
      await refreshLogs();
      return;
    }
    const pageNumber = event.target.closest(".page-number");
    if (pageNumber && !pageNumber.classList.contains("is-disabled")) {
      state.logs.page = Number(pageNumber.dataset.page);
      await refreshLogs();
      return;
    }
    const executionRow = event.target.closest("#live-executions-table tr");
    if (executionRow?.dataset?.taskId) {
      await openAuditDrawer(executionRow.dataset.taskId);
      return;
    }
    const removeTp = event.target.closest(".remove-tp-step");
    if (removeTp) {
      removeTp.closest(".form-grid").remove();
      return;
    }
    if (event.target.classList.contains("modal")) {
      event.target.classList.add("hidden");
    }
  });

  document.addEventListener("keydown", async (event) => {
    if (event.key === "Escape") closeAuditDrawer();
    if (event.target.closest("#live-executions-table tr") && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      await openAuditDrawer(event.target.closest("tr").dataset.taskId);
    }
    if (event.target.closest("#logs-table tr") && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      const row = event.target.closest("tr");
      const log = state.logsPage?.items?.find((item) => item.id === row.dataset.logId);
      if (log) renderLogDetail(log);
    }
  });
}

async function bootstrap() {
  populatePreferenceControls();
  applyDocumentPreferences();
  applyStaticTranslations();
  bindTabs();
  bindPreferences();
  bindStaticActions();
  addTakeProfitStep();
  renderBuilderActionSegments();
  await refreshDashboard();
  await Promise.all([refreshPositions(), refreshLogs(), refreshHealth()]);
  connectLiveStream();
}

bootstrap().catch((error) => {
  setStatus(`Load failed: ${error.message}`, true);
});
