"""systemd .service 欄位定義、分層與範本。

欄位說明參考：
- systemd.service(5)
- systemd.unit(5)（[Unit] / [Install]）
- systemd.exec(5)、systemd.kill(5)、systemd.resource-control(5)
"""

SECTIONS_ORDER = ["[Unit]", "[Service]", "[Install]"]

SECTION_LABELS = {
    "[Unit]": "Unit 單元",
    "[Service]": "Service 服務",
    "[Install]": "Install 安裝",
}

KEY_DEFS: dict[str, dict[str, dict]] = {
    "[Unit]": {
        "Description": {
            "desc": (
                "服務的人類可讀名稱。\n"
                "顯示於 systemctl status、journal 訊息等處。\n"
                "（systemd.unit(5) — 所有 unit 類型共用）"
            ),
            "example": "BMC Hello Heartbeat Service",
            "required": True,
            "tier": "essential",
        },
        "Documentation": {
            "desc": (
                "文件 URI，多個以空白分隔。\n"
                "可用 man:、file:、http(s):、info: 等 URI scheme。\n"
                "（systemd.unit(5)）"
            ),
            "example": "man:bmc-hello(8) https://github.com/openbmc/docs",
            "tier": "common",
        },
        "After": {
            "desc": (
                "啟動順序：在本服務啟動「之前」，先啟動列出的 unit。\n"
                "僅影響排序，不是強依賴；對方不存在或失敗，本服務仍會嘗試啟動。\n"
                "與 Requires= 不同：Requires 是依賴關係，After 只是「誰先誰後」。\n"
                "（systemd.unit(5)）"
            ),
            "example": "dbus.service network.target",
            "tier": "essential",
        },
        "Before": {
            "desc": (
                "啟動順序：在本服務啟動「之後」，才啟動列出的 unit。\n"
                "同樣只影響排序，不保證對方一定成功。\n"
                "（systemd.unit(5)）"
            ),
            "example": "multi-user.target",
            "tier": "common",
        },
        "Wants": {
            "desc": (
                "弱依賴：啟動本服務時，一併嘗試啟動列出的 unit。\n"
                "對方啟動失敗不會導致本服務失敗；對方停止也不會自動停止本服務。\n"
                "（systemd.unit(5)）"
            ),
            "example": "network.target",
            "tier": "common",
        },
        "Requires": {
            "desc": (
                "強依賴：列出的 unit 必須處於 active，本服務才能啟動。\n"
                "若對方停止或啟動失敗，本服務也會被停止。\n"
                "OpenBMC 服務通常 Requires=dbus.service。\n"
                "（systemd.unit(5)）"
            ),
            "example": "dbus.service",
            "tier": "essential",
        },
        "Conflicts": {
            "desc": (
                "互斥：不能與列出的 unit 同時處於 active。\n"
                "啟動本服務會停止對方；系統預設也與 shutdown.target 互斥。\n"
                "（systemd.unit(5)）"
            ),
            "example": "shutdown.target reboot.target",
            "tier": "common",
        },
        "ConditionPathExists": {
            "desc": (
                "啟動條件：只有當指定路徑存在時才嘗試啟動。\n"
                "路徑前加「!」表示「不存在時才啟動」。\n"
                "適合依硬體裝置節點（如 /dev/i2c-N）決定是否啟動的服務。\n"
                "（systemd.unit(5)）"
            ),
            "example": "/dev/i2c-0",
            "tier": "common",
        },
    },
    "[Service]": {
        "Type": {
            "desc": (
                "服務如何通知 systemd「啟動完成」：\n"
                "  simple  — fork 後即視為啟動（預設；BMC 前台 daemon 常用）\n"
                "  exec    — 執行檔 execve() 成功後才視為啟動（較能抓到缺檔/User 錯誤）\n"
                "  forking — 傳統 UNIX daemon，父行程退出後才算啟動（建議配 PIDFile=）\n"
                "  oneshot — 跑完即退出；常配 RemainAfterExit=yes 做初始化腳本\n"
                "  dbus    — 取得 BusName= 後才算就緒；會自動依賴 dbus.socket\n"
                "  notify  — 程序須 sd_notify(\"READY=1\") 通知就緒\n"
                "  idle    — 延遲到系統空閒再啟動（主要改善主控台輸出順序）\n"
                "（systemd.service(5) — Type=）"
            ),
            "choices": ["simple", "exec", "forking", "oneshot", "dbus", "notify", "idle"],
            "default": "simple",
            "required": True,
            "tier": "essential",
        },
        "ExecStart": {
            "desc": (
                "服務啟動時執行的命令（必須絕對路徑）。\n"
                "非 oneshot 時只能有一條；oneshot 可寫多條依序執行。\n"
                "前綴「-」= 失敗不影響後續；「@」= 隱藏 argv[0]；「+」= 略過部分權限限制。\n"
                "若未設定 ExecStart=，須有 RemainAfterExit=yes 且至少一條 ExecStop=。\n"
                "（systemd.service(5) — ExecStart=）"
            ),
            "example": "/usr/local/bin/bmc-hello",
            "required": True,
            "tier": "essential",

        },
        "ExecStop": {
            "desc": (
                "停止服務時執行的命令（可多條）。\n"
                "若未設定，systemd 改送 KillSignal= 終止主程序。\n"
                "應為同步等待程序結束的命令，而非只送非同步信號。\n"
                "僅在服務曾成功啟動後才會執行。\n"
                "（systemd.service(5) — ExecStop=）"
            ),
            "example": "/usr/bin/kill -TERM $MAINPID",
            "tier": "common",

        },
        "ExecReload": {
            "desc": (
                "systemctl reload 時執行的命令。\n"
                "可設定 $MAINPID 指向主程序。\n"
                "官方建議：優先使用 Type=notify-reload，或執行會「等待 reload 完成」的命令，"
                "而非只 kill -HUP 的非同步做法。\n"
                "（systemd.service(5) — ExecReload=）"
            ),
            "example": "/bin/kill -HUP $MAINPID",
            "tier": "common",

        },
        "ExecStartPre": {
            "desc": (
                "在 ExecStart= 之前執行的準備命令（可多條、依序）。\n"
                "任一條失敗（且未加「-」前綴）則不執行 ExecStart=，unit 視為失敗。\n"
                "不可啟動長期運行的程序（會在 ExecStart 前被殺掉）。\n"
                "（systemd.service(5) — ExecStartPre=）"
            ),
            "example": "-/bin/mkdir -p /run/bmc",
            "tier": "common",

        },
        "ExecStartPost": {
            "desc": (
                "在 ExecStart= 判定「啟動成功」之後執行的命令。\n"
                "成功條件依 Type= 而定（simple=程序已 fork、notify=收到 READY=1 等）。\n"
                "（systemd.service(5) — ExecStartPost=）"
            ),
            "example": "/usr/bin/logger BMC service started",
            "tier": "common",

        },
        "Restart": {
            "desc": (
                "程序退出後是否自動重啟：\n"
                "  no          — 不重啟（預設）\n"
                "  on-success  — 僅正常退出（exit 0 等）時重啟\n"
                "  on-failure  — 非正常退出、逾時、watchdog 時重啟（daemon 推薦）\n"
                "  on-abnormal — 被信號殺死或逾時時重啟\n"
                "  always      — 無條件重啟（含 systemctl stop 後也會重啟，慎用）\n"
                "systemctl stop 不會觸發重啟。受 StartLimitBurst 速率限制。\n"
                "（systemd.service(5) — Restart=）"
            ),
            "choices": ["no", "on-success", "on-failure", "on-abnormal", "always"],
            "default": "no",
            "tier": "essential",
        },
        "RestartSec": {
            "desc": (
                "重啟前等待時間，避免 crash loop。\n"
                "可寫秒數或時間跨度（如 5min 20s），預設 100ms。\n"
                "（systemd.service(5) — RestartSec=）"
            ),
            "example": "3",
            "default": "100ms",
            "tier": "common",
        },
        "User": {
            "desc": (
                "以指定使用者身分執行服務程序。\n"
                "省略則以 root 執行。透過 NSS 查詢可能產生隱性依賴延遲。\n"
                "（systemd.exec(5) — User=）"
            ),
            "example": "bmc",
            "tier": "common",
        },
        "Group": {
            "desc": (
                "以指定群組執行。省略則使用 User= 的主群組。\n"
                "（systemd.exec(5) — Group=）"
            ),
            "example": "bmc",
            "tier": "common",
        },
        "WorkingDirectory": {
            "desc": (
                "服務程序的工作目錄。\n"
                "「~」會展開為 User= 的家目錄。\n"
                "（systemd.exec(5) — WorkingDirectory=）"
            ),
            "example": "/var/lib/bmc",
            "tier": "common",
        },
        "Environment": {
            "desc": (
                "設定環境變數，格式 KEY=value，多個以空白分隔。\n"
                "含空白的值請加引號：OPTS=\"-v -d\"。\n"
                "（systemd.exec(5) — Environment=）"
            ),
            "example": "BMC_LOG_LEVEL=info",
            "tier": "common",

        },
        "EnvironmentFile": {
            "desc": (
                "從檔案載入環境變數（每行 KEY=value）。\n"
                "路徑前加「-」表示檔案不存在時不報錯。\n"
                "（systemd.exec(5) — EnvironmentFile=）"
            ),
            "example": "-/etc/bmc/env",
            "tier": "common",
        },
        "StandardOutput": {
            "desc": (
                "標準輸出 (stdout) 去向：\n"
                "  journal  — 寫入 systemd journal（journalctl 可查，BMC 常用）\n"
                "  null     — 丟棄\n"
                "  inherit  — 繼承父程序\n"
                "  tty      — 目前 tty\n"
                "  file:/path — 寫入檔案（須絕對路徑）\n"
                "（systemd.exec(5) — StandardOutput=）"
            ),
            "choices": ["journal", "null", "tty", "inherit"],
            "default": "journal",
            "tier": "essential",
        },
        "StandardError": {
            "desc": (
                "標準錯誤 (stderr) 去向，選項同 StandardOutput=。\n"
                "journal+console 可同時寫 journal 與主控台。\n"
                "（systemd.exec(5) — StandardError=）"
            ),
            "choices": ["journal", "null", "tty", "inherit", "journal+console"],
            "default": "journal",
            "tier": "essential",
        },
        "SyslogIdentifier": {
            "desc": (
                "寫入 journal 時使用的識別標籤。\n"
                "可用 journalctl -t <名稱> 過濾本服務日誌。\n"
                "（systemd.exec(5) — SyslogIdentifier=）"
            ),
            "example": "bmc-hello",
            "tier": "common",
        },
        "KillSignal": {
            "desc": (
                "停止服務時送給主程序的信號（未設定 ExecStop= 時使用）。\n"
                "預設 SIGTERM，讓程序有機會優雅關閉。\n"
                "逾時後可能再送 SIGKILL（見 TimeoutStopSec=）。\n"
                "（systemd.kill(5) — KillSignal=）"
            ),
            "choices": ["SIGTERM", "SIGKILL", "SIGHUP", "SIGINT"],
            "default": "SIGTERM",
            "tier": "common",
        },
        "TimeoutStartSec": {
            "desc": (
                "啟動逾時：若在此時間內未完成啟動（依 Type= 判定），視為失敗並關閉。\n"
                "寫 infinity 可停用。oneshot 預設停用。\n"
                "notify 服務可送 EXTEND_TIMEOUT_USEC 延長。\n"
                "（systemd.service(5) — TimeoutStartSec=）"
            ),
            "example": "30s",
            "tier": "common",
        },
        "TimeoutStopSec": {
            "desc": (
                "停止逾時：ExecStop= 每條命令與整體停止的等待上限。\n"
                "逾時後強制 SIGKILL。寫 infinity 可停用。\n"
                "（systemd.service(5) — TimeoutStopSec=）"
            ),
            "example": "30s",
            "tier": "common",
        },
        "RemainAfterExit": {
            "desc": (
                "布林值：主程序退出後，服務是否仍視為 active。\n"
                "Type=oneshot 做「開機初始化」時通常設 yes，"
                "否則腳本跑完服務會立刻變 dead。\n"
                "（systemd.service(5) — RemainAfterExit=）"
            ),
            "choices": ["yes", "no"],
            "default": "no",
            "tier": "common",
            "show_when_type": ["oneshot"],
        },
        "PIDFile": {
            "desc": (
                "主程序 PID 檔路徑，Type=forking 時建議設定。\n"
                "systemd 在啟動後從此檔讀取 PID 以追蹤主程序。\n"
                "systemd 不會寫入此檔，但服務關閉後可能刪除它。\n"
                "現代專案更推薦 notify/dbus/simple，少用 PID 檔。\n"
                "（systemd.service(5) — PIDFile=）"
            ),
            "example": "/run/bmc.pid",
            "tier": "common",
            "show_when_type": ["forking"],
        },
        "BusName": {
            "desc": (
                "D-Bus well-known name，Type=dbus 時為必填。\n"
                "systemd 在程序取得此 bus name 後才視為啟動完成。\n"
                "會自動加入對 dbus.socket 的依賴。\n"
                "釋放 bus name 後服務視為不再運作，可能收到 SIGTERM。\n"
                "（systemd.service(5) — BusName=）"
            ),
            "example": "xyz.openbmc_project.Example",
            "tier": "essential",
            "show_when_type": ["dbus"],

        },
        "WatchdogSec": {
            "desc": (
                "Watchdog 逾時：啟動完成後，程序須定期 sd_notify(\"WATCHDOG=1\")。\n"
                "逾時未收到則視為當機，以 SIGABRT 終止；可配 Restart= 自動重啟。\n"
                "程序可從環境變數 WATCHDOG_USEC 得知設定值。0 = 停用（預設）。\n"
                "（systemd.service(5) — WatchdogSec=）"
            ),
            "example": "30s",
            "tier": "advanced",
        },
        "LimitNOFILE": {
            "desc": (
                "程序可開啟的檔案描述符上限（類似 ulimit -n）。\n"
                "影響 socket、檔案 handle 數量。\n"
                "（systemd.exec(5) / systemd.resource-control(5) — LimitNOFILE=）"
            ),
            "example": "65536",
            "tier": "advanced",
        },
        "PrivateTmp": {
            "desc": (
                "為服務提供獨立的 /tmp 與 /var/tmp 目錄。\n"
                "不同服務互相隔離，提高安全性。\n"
                "（systemd.exec(5) — PrivateTmp=）"
            ),
            "choices": ["yes", "no"],
            "tier": "advanced",
        },
        "CapabilityBoundingSet": {
            "desc": (
                "限制 Linux capabilities 邊界集合。\n"
                "設為空白繼承預設；設為「=」清空所有 capability。\n"
                "常見：CAP_NET_ADMIN CAP_SYS_RAWIO CAP_DAC_READ_SEARCH\n"
                "（systemd.exec(5) — CapabilityBoundingSet=）"
            ),
            "example": "CAP_NET_ADMIN CAP_SYS_RAWIO",
            "tier": "advanced",

        },
        "ReadWritePaths": {
            "desc": (
                "在 ProtectSystem=strict 等唯讀根目錄設定下，\n"
                "額外允許讀寫的路徑列表。\n"
                "（systemd.exec(5) — ReadWritePaths=）"
            ),
            "example": "/var/lib/bmc /run/bmc",
            "tier": "advanced",

        },
        "Nice": {
            "desc": (
                "程序 nice 值（-20 最高優先 ~ 19 最低），預設 0。\n"
                "（systemd.exec(5) — Nice=）"
            ),
            "example": "-5",
            "tier": "advanced",
        },
    },
    "[Install]": {
        "WantedBy": {
            "desc": (
                "systemctl enable 時，在列出的 target 的 .wants/ 目錄建立 symlink。\n"
                "該 target 啟動時會一併啟動本服務。\n"
                "  multi-user.target — 多使用者模式（無 GUI 的伺服器/BMC 常用）\n"
                "  graphical.target  — 圖形界面模式\n"
                "（systemd.unit(5) — WantedBy=）"
            ),
            "example": "multi-user.target",
            "required": True,
            "tier": "essential",
        },
        "RequiredBy": {
            "desc": (
                "與 Requires= 相反：列出的 target 強依賴本服務。\n"
                "enable 時在對方 .requires/ 建立 symlink。\n"
                "（systemd.unit(5) — RequiredBy=）"
            ),
            "example": "graphical.target",
            "tier": "common",
        },
        "Also": {
            "desc": (
                "enable/disable 本服務時，一併 enable/disable 列出的其他 unit。\n"
                "（systemd.unit(5) — Also=）"
            ),
            "example": "bmc-helper.socket",
            "tier": "common",
        },
        "Alias": {
            "desc": (
                "服務別名：enable 時額外建立指向本服務的 symlink。\n"
                "可用 systemctl start <別名> 操作同一服務。\n"
                "（systemd.unit(5) — Alias=）"
            ),
            "example": "sensor-monitor.service",
            "tier": "common",
        },
    },
}

TIER_LABELS = {
    "essential": "基本欄位",
    "common": "常用欄位",
    "advanced": "進階欄位",
}

TIER_ORDER = ["essential", "common", "advanced"]

DEFAULT_HELP = (
    "點選左側任一欄位，此處會顯示說明。\n"
    "內容依據 systemd.service(5) / systemd.unit(5) 等官方文件整理。"
)

TEMPLATES: dict[str, dict] = {
    # ── 空白 ──────────────────────────────────────────────────────────────────
    "空白": {},

    # ── 1. 簡單常駐服務 ───────────────────────────────────────────────────────
    # 最常見的 daemon 模式：前台執行、crash 自動重啟。
    # 對應 systemd.service(5) 中 Type=simple 的典型範例。
    "簡單常駐服務": {
        "[Unit]": {
            "Description": "My Background Service",
            "After": "network.target",
        },
        "[Service]": {
            "Type": "simple",
            "ExecStart": "/usr/local/bin/my-service",
            "Restart": "on-failure",
            "RestartSec": "5",
            "StandardOutput": "journal",
            "StandardError": "journal",
            "SyslogIdentifier": "my-service",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 2. 以一般使用者執行（降權 daemon）────────────────────────────────────
    # 服務以非 root 使用者執行，搭配 PrivateTmp 增加隔離。
    # 適合需要 least-privilege 的網路服務或資料處理服務。
    "降權使用者服務": {
        "[Unit]": {
            "Description": "My Unprivileged Service",
            "After": "network.target",
        },
        "[Service]": {
            "Type": "simple",
            "User": "nobody",
            "Group": "nogroup",
            "ExecStart": "/usr/local/bin/my-service",
            "Restart": "on-failure",
            "RestartSec": "5",
            "PrivateTmp": "yes",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 3. 需要通知就緒的服務（Type=notify）──────────────────────────────────
    # 程序初始化完成後呼叫 sd_notify("READY=1")，
    # 其他 After= 本服務的 unit 才會開始啟動。
    # 對應 sd_notify(3) 官方建議做法。
    "通知就緒服務 (notify)": {
        "[Unit]": {
            "Description": "My Notify-Ready Service",
            "After": "network.target",
        },
        "[Service]": {
            "Type": "notify",
            "ExecStart": "/usr/local/bin/my-service",
            "Restart": "on-failure",
            "RestartSec": "5",
            "WatchdogSec": "30s",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 4. D-Bus 服務 ─────────────────────────────────────────────────────────
    # 取得 BusName 後才視為就緒；自動建立對 dbus.socket 的依賴。
    # 對應 systemd.service(5) Type=dbus 範例。
    "D-Bus 服務": {
        "[Unit]": {
            "Description": "My D-Bus Service",
            "After": "dbus.service",
            "Requires": "dbus.service",
        },
        "[Service]": {
            "Type": "dbus",
            "BusName": "com.example.MyService",
            "ExecStart": "/usr/libexec/my-dbus-service",
            "Restart": "on-failure",
            "RestartSec": "3",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 5. Oneshot 初始化腳本 ─────────────────────────────────────────────────
    # 開機時執行一次、不常駐；RemainAfterExit=yes 讓服務維持 active 狀態，
    # 讓其他 Requires= 本服務的 unit 可以正常依賴。
    # 對應 systemd.service(5) Type=oneshot 範例。
    "Oneshot 初始化腳本": {
        "[Unit]": {
            "Description": "My One-shot Initialization",
            "After": "local-fs.target",
        },
        "[Service]": {
            "Type": "oneshot",
            "ExecStart": "/usr/local/bin/my-init-script.sh",
            "RemainAfterExit": "yes",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 6. 傳統 Forking Daemon ────────────────────────────────────────────────
    # fork 後父程序退出，PIDFile 讓 systemd 追蹤子程序。
    # 適合舊式 daemon（Apache httpd、sshd 等預設模式）。
    # 對應 systemd.service(5) Type=forking 範例。
    "傳統 Forking Daemon": {
        "[Unit]": {
            "Description": "My Traditional Forking Daemon",
            "After": "network.target",
        },
        "[Service]": {
            "Type": "forking",
            "PIDFile": "/run/my-daemon/my-daemon.pid",
            "ExecStartPre": "-/bin/mkdir -p /run/my-daemon",
            "ExecStart": "/usr/sbin/my-daemon --daemonize --pidfile /run/my-daemon/my-daemon.pid",
            "Restart": "on-failure",
            "RestartSec": "5",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },

    # ── 7. 網路服務（等待網路完全就緒）──────────────────────────────────────
    # network-online.target 比 network.target 更嚴格：
    # 確保網路介面取得 IP 後才啟動（需 systemd-networkd-wait-online 等服務）。
    # 對應 systemd.network(5) 官方建議的網路依賴寫法。
    "網路相關服務": {
        "[Unit]": {
            "Description": "My Network-Dependent Service",
            "After": "network-online.target",
            "Wants": "network-online.target",
        },
        "[Service]": {
            "Type": "simple",
            "ExecStart": "/usr/local/bin/my-network-service",
            "Restart": "on-failure",
            "RestartSec": "10",
            "StandardOutput": "journal",
            "StandardError": "journal",
        },
        "[Install]": {
            "WantedBy": "multi-user.target",
        },
    },
}
