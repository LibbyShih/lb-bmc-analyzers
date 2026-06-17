"""meson.build 函式/欄位定義，依據 Meson Reference Manual 整理。
https://mesonbuild.com/Reference-manual_functions.html
"""

REF_MANUAL = "https://mesonbuild.com/Reference-manual_functions.html"

# project() 支援的語言（Reference-manual_functions.html#project）
LANGUAGE_CHOICES = [
    "c",
    "cpp",
    "cuda",
    "cython",
    "d",
    "objc",
    "objcpp",
    "fortran",
    "java",
    "cs",
    "swift",
    "nasm",
    "masm",
    "linearasm",
    "vala",
    "rust",
]

# BMC 專案常用語言（UI 預設顯示）
LANGUAGE_CHOICES_COMMON = ["c", "cpp"]

TARGET_KIND_CHOICES = ["executable", "library", "static_library", "shared_library"]

DEPENDENCY_METHOD_CHOICES = ["", "auto", "pkg-config", "cmake", "qmake", "system"]

# project() default_options 常見預設（Reference-manual_functions.html#project_default_options）
DEFAULT_OPTION_PRESETS = [
    "cpp_std=c++17",
    "cpp_std=c++20",
    "warning_level=3",
    "buildtype=debugoptimized",
    "default_library=static",
    "default_library=shared",
]

PROJECT_FIELDS = {
    "name": {
        "desc": (
            "專案名稱，project() 第一個位置參數（project_name）。\n"
            "僅供描述用途，建議與 tarball 或 pkg-config 名稱一致。\n"
            "官方文件：Reference-manual_functions.html#project"
        ),
        "example": "bmc-round0",
        "required": True,
        "ref": f"{REF_MANUAL}#project",
    },
    "languages": {
        "desc": (
            "專案使用的程式語言，project() 第二個起的位置參數（language...）。\n"
            "自 0.40.0 起可省略；支援 c、cpp、cuda、cython、d、objc、objcpp、\n"
            "fortran、java、cs、swift、nasm、masm、linearasm、vala、rust。\n"
            "官方文件：Reference-manual_functions.html#project"
        ),
        "example": "cpp",
        "required": True,
        "ref": f"{REF_MANUAL}#project",
    },
    "version": {
        "desc": (
            "專案版本字串，project() 的 version 關鍵字參數。\n"
            "可透過 meson.project_version() 在 build 檔中讀取。\n"
            "官方文件：Reference-manual_functions.html#project_version"
        ),
        "example": "0.1",
        "ref": f"{REF_MANUAL}#project_version",
    },
    "meson_version": {
        "desc": (
            "要求的 Meson 最低版本，project() 的 meson_version 關鍵字參數。\n"
            "格式如 >=0.63.0。\n"
            "官方文件：Reference-manual_functions.html#project_meson_version"
        ),
        "example": ">=0.63.0",
        "ref": f"{REF_MANUAL}#project_meson_version",
    },
    "default_options": {
        "desc": (
            "編譯預設選項，project() 的 default_options 關鍵字參數。\n"
            "每行一筆 key=value，格式同 meson configure 選項。\n"
            "僅在首次執行 meson setup 時生效；命令列參數會覆寫。\n"
            "常見：cpp_std=c++17、warning_level=3、buildtype=debugoptimized。\n"
            "官方文件：Reference-manual_functions.html#project_default_options"
        ),
        "example": "cpp_std=c++17",
        "ref": f"{REF_MANUAL}#project_default_options",
    },
}

DEPENDENCY_FIELDS = {
    "var_name": {
        "desc": (
            "依賴變數名稱（選填）。留空表示匿名依賴，\n"
            "存檔時會直接內嵌在使用它的 target 呼叫中，不產生獨立賦值行。"
        ),
        "example": "boost_dep",
    },
    "name": {
        "desc": (
            "依賴套件名稱，dependency() 第一個位置參數（names...）。\n"
            "Meson 以 pkg-config 尋找，失敗時嘗試 CMake。\n"
            "自 0.60.0 起可傳多個名稱，依序嘗試直到找到為止。\n"
            "官方文件：Reference-manual_functions.html#dependency"
        ),
        "example": "boost",
        "required": True,
        "ref": f"{REF_MANUAL}#dependency",
    },
    "modules": {
        "desc": (
            "pkg-config 子模組/元件名稱（部分依賴如 boost 使用）。\n"
            "對應 dependency() 的 modules 關鍵字；每行一筆。\n"
            "範例：boost 的 system、thread。"
        ),
        "example": "system",
    },
    "method": {
        "desc": (
            "尋找依賴的方法，dependency() 的 method 關鍵字參數。\n"
            "預設 auto；可設 pkg-config、cmake、qmake 等（依後端支援）。\n"
            "官方文件：Reference-manual_functions.html#dependency_method"
        ),
        "example": "pkg-config",
        "default": "auto",
        "ref": f"{REF_MANUAL}#dependency_method",
    },
    "version": {
        "desc": (
            "版本限制字串，dependency() 的 version 關鍵字參數。\n"
            "格式：比較運算子 + 版本，如 >=1.70、<=2.3.5、3.1.4。\n"
            "官方文件：Reference-manual_functions.html#dependency_version"
        ),
        "example": ">=1.70",
        "ref": f"{REF_MANUAL}#dependency_version",
    },
    "required": {
        "desc": (
            "找不到依賴時是否視為錯誤，dependency() 的 required 關鍵字參數。\n"
            "設 false 時找不到仍繼續建置，回傳 found() 為 false 的 dep 物件。\n"
            "官方文件：Reference-manual_functions.html#dependency_required"
        ),
        "default": "true",
        "ref": f"{REF_MANUAL}#dependency_required",
    },
}

FILE_GROUP_FIELDS = {
    "var_name": {
        "desc": (
            "files() 回傳值的變數名稱（必填）。\n"
            "產生 var = files('a.cpp', 'b.cpp') 賦值行。\n"
            "file 物件會記住定義時的子目錄，可在其他 target 中引用。\n"
            "官方文件：Reference-manual_functions.html#files"
        ),
        "example": "src_files",
        "required": True,
        "ref": f"{REF_MANUAL}#files",
    },
    "paths": {
        "desc": (
            "檔案路徑清單，files() 的位置參數（file...），每行一筆。\n"
            "相對於目前 meson.build 所在目錄。\n"
            "官方文件：Reference-manual_functions.html#files"
        ),
        "example": "src/foo.cpp",
        "required": True,
        "ref": f"{REF_MANUAL}#files",
    },
}

TARGET_FIELDS = {
    "var_name": {
        "desc": (
            "Target 變數名稱（選填）。被其他 target 的 link_with 引用時需要填，\n"
            "填了會產生 var = executable(...) 賦值行，否則直接呼叫。"
        ),
        "example": "mylib",
    },
    "kind": {
        "desc": (
            "Build target 類型：\n"
            "• executable — 執行檔（Reference-manual_functions.html#executable）\n"
            "• library — 依 default_library 選項建 static/shared（#library）\n"
            "• static_library — 靜態函式庫（#static_library）\n"
            "• shared_library — 動態函式庫（#shared_library）"
        ),
        "example": "executable",
        "required": True,
    },
    "name": {
        "desc": (
            "Build target 唯一名稱，第一個位置參數（target_name）。\n"
            "executable()/library()/static_library()/shared_library() 皆同。\n"
            "官方文件：Reference-manual_functions.html#executable"
        ),
        "example": "bmc-hello",
        "required": True,
        "ref": f"{REF_MANUAL}#executable",
    },
    "sources": {
        "desc": (
            "原始碼檔案清單。可為位置參數（source...）或 sources 關鍵字。\n"
            "支援字串路徑、files() 變數引用、或兩者混用。\n"
            "每行一筆相對路徑；勾選下方 files 群組可引用已定義的 file 物件。\n"
            "官方文件：Reference-manual_functions.html#executable_sources"
        ),
        "example": "src/heartbeat.cpp",
        "required": True,
        "ref": f"{REF_MANUAL}#executable_sources",
    },
    "dependencies": {
        "desc": (
            "依賴物件清單，dependencies 關鍵字參數。\n"
            "引用依賴池中已命名的 dependency() 變數，或行內匿名 dependency()。\n"
            "官方文件：Reference-manual_functions.html#executable_dependencies"
        ),
        "ref": f"{REF_MANUAL}#executable_dependencies",
    },
    "link_with": {
        "desc": (
            "連結的函式庫清單，link_with 關鍵字參數。\n"
            "引用本專案建置的 shared 或 static library target 變數。\n"
            "官方文件：Reference-manual_functions.html#executable_link_with"
        ),
        "ref": f"{REF_MANUAL}#executable_link_with",
    },
    "install": {
        "desc": (
            "是否安裝此 target 的輸出，install 關鍵字參數。\n"
            "設 true 時執行 meson install 會一併安裝。\n"
            "官方文件：Reference-manual_functions.html#executable_install"
        ),
        "default": "false",
        "ref": f"{REF_MANUAL}#executable_install",
    },
}

INSTALL_DATA_FIELDS = {
    "paths": {
        "desc": (
            "要安裝的資料檔案清單，install_data() 位置參數（file...），每行一筆。\n"
            "僅能安裝來源樹中的靜態檔案；產生檔請用 custom_target 等的 install_dir。\n"
            "官方文件：Reference-manual_functions.html#install_data"
        ),
        "example": "systemd/bmc-hello.service",
        "required": True,
        "ref": f"{REF_MANUAL}#install_data",
    },
    "install_dir": {
        "desc": (
            "安裝目的目錄，install_dir 關鍵字參數。\n"
            "可為絕對路徑或相對於 prefix 的路徑。\n"
            "官方文件：Reference-manual_functions.html#install_data_install_dir"
        ),
        "example": "/lib/systemd/system/",
        "ref": f"{REF_MANUAL}#install_data_install_dir",
    },
}

INSTALL_HEADERS_FIELDS = {
    "paths": {
        "desc": (
            "要安裝的標頭檔清單，install_headers() 位置參數（file...），每行一筆。\n"
            "官方文件：Reference-manual_functions.html#install_headers"
        ),
        "example": "include/bmc.h",
        "required": True,
        "ref": f"{REF_MANUAL}#install_headers",
    },
    "subdir": {
        "desc": (
            "安裝到 include 目錄下的子目錄，subdir 關鍵字參數。\n"
            "例如 subdir : 'myproj' → {prefix}/include/myproj/。\n"
            "官方文件：Reference-manual_functions.html#install_headers_subdir"
        ),
        "example": "bmc",
        "ref": f"{REF_MANUAL}#install_headers_subdir",
    },
    "install_dir": {
        "desc": (
            "覆寫安裝根目錄，install_dir 關鍵字參數。\n"
            "與 subdir 搭配可安裝到自訂路徑，如 cust/myproj。\n"
            "官方文件：Reference-manual_functions.html#install_headers_install_dir"
        ),
        "example": "cust",
        "ref": f"{REF_MANUAL}#install_headers_install_dir",
    },
    "preserve_path": {
        "desc": (
            "保留子目錄結構，preserve_path 關鍵字參數（自 0.63.0）。\n"
            "設 true 時 proj/kola.h 安裝到 include/proj/ 而非扁平化。\n"
            "等同 GNU Automake 的 nobase 選項。\n"
            "官方文件：Reference-manual_functions.html#install_headers_preserve_path"
        ),
        "default": "false",
        "ref": f"{REF_MANUAL}#install_headers_preserve_path",
    },
}

FUNCTION_OVERVIEW = {
    "project": (
        "project() — 每個 Meson 專案的第一個呼叫，初始化建置系統。\n"
        f"文件：{REF_MANUAL}#project"
    ),
    "dependency": (
        "dependency() — 尋找外部依賴（函式庫等），預設用 pkg-config，\n"
        "失敗時嘗試 CMake。\n"
        f"文件：{REF_MANUAL}#dependency"
    ),
    "files": (
        "files() — 將路徑字串轉為 file 物件，記住定義子目錄，\n"
        "可在任意 target 的 sources 中引用。\n"
        f"文件：{REF_MANUAL}#files"
    ),
    "executable": (
        "executable() — 建立執行檔。第一參數為名稱，其餘為原始碼。\n"
        f"文件：{REF_MANUAL}#executable"
    ),
    "library": (
        "library() — 依 default_library 選項建 static 或 shared 函式庫。\n"
        f"文件：{REF_MANUAL}#library"
    ),
    "static_library": (
        "static_library() — 建立靜態函式庫（.a / .lib）。\n"
        f"文件：{REF_MANUAL}#static_library"
    ),
    "shared_library": (
        "shared_library() — 建立動態/shared 函式庫（.so / .dll / .dylib）。\n"
        f"文件：{REF_MANUAL}#shared_library"
    ),
    "install_data": (
        "install_data() — 從來源樹安裝靜態資料檔。\n"
        f"文件：{REF_MANUAL}#install_data"
    ),
    "install_headers": (
        "install_headers() — 安裝標頭檔到 include 目錄。\n"
        f"文件：{REF_MANUAL}#install_headers"
    ),
}

DEFAULT_HELP = (
    "點選左側任一欄位，此處會顯示說明。\n"
    "內容依據 Meson Reference Manual（mesonbuild.com）整理。\n"
    f"完整函式列表：{REF_MANUAL}"
)

def _empty_template_extras() -> dict:
    return {
        "file_groups": [],
        "install_data": [],
        "install_headers": [],
        "unrecognized": "",
    }


TEMPLATES: dict = {
    "空白": None,
    "單一執行檔 + 系統依賴": {
        "project": {
            "name": "my-project",
            "languages": ["cpp"],
            "version": "0.1",
            "meson_version": "",
            "default_options": ["cpp_std=c++17"],
        },
        "dependencies": [
            {
                "var_name": "thread_dep",
                "name": "threads",
                "modules": [],
                "method": "",
                "version": "",
                "required": True,
            },
        ],
        "file_groups": [],
        "targets": [
            {
                "kind": "executable",
                "var_name": None,
                "name": "my-app",
                "sources": ["src/main.cpp"],
                "file_refs": [],
                "dep_refs": [0],
                "link_with_refs": [],
                "install": True,
            },
        ],
        **_empty_template_extras(),
    },
    "函式庫 + 執行檔": {
        "project": {
            "name": "my-project",
            "languages": ["cpp"],
            "version": "0.1",
            "meson_version": "",
            "default_options": [],
        },
        "dependencies": [],
        "file_groups": [],
        "targets": [
            {
                "kind": "static_library",
                "var_name": "mylib",
                "name": "mylib",
                "sources": ["src/lib.cpp"],
                "file_refs": [],
                "dep_refs": [],
                "link_with_refs": [],
                "install": False,
            },
            {
                "kind": "executable",
                "var_name": None,
                "name": "my-app",
                "sources": ["src/main.cpp"],
                "file_refs": [],
                "dep_refs": [],
                "link_with_refs": [0],
                "install": True,
            },
        ],
        **_empty_template_extras(),
    },
    "純安裝資料": {
        "project": {
            "name": "my-data",
            "languages": ["c"],
            "version": "",
            "meson_version": "",
            "default_options": [],
        },
        "dependencies": [],
        "file_groups": [],
        "targets": [],
        "install_data": [{"paths": ["data/config.json"], "install_dir": "/etc/my-app/"}],
        "install_headers": [],
        "unrecognized": "",
    },
}
