# -*- coding: utf-8 -*-
"""
把「翻译」作为**真正的第三个标签页**接进 截图OCR 页面。

做法（不改 Umi 任何文件）：
  1. 从 TabBar 里取出原生标签用的 delegate 组件，克隆一个「翻译」标签 ->
     TabBar.addItem()，选中态 / 互斥高亮全部由 Umi 的 TabBar 控制器管理
  2. 把 EmbedPanel.qml 通过 SwipeView.addItem() 变成第三个页面，切换动画也是原生的

定位方式（不依赖文件名 / 版本号）：
  * 主窗口     : contentItem 上带 theme 属性的 QQuickWindow
  * 截图OCR页  : 带 msnState 属性的 Item（全项目只有 ScreenshotOCR.qml 有）
  * 标签栏     : 该页里的 TabPanel -> TabBar
  * 内容区     : TabPanel 的直接子项里那个 SwipeView
  * 记录模型   : TabPanel.tabsModel 中 key == "ocrResult" 的那一页

任何一步失败都只写日志，不影响 Umi 启动。
"""

import os

from PySide2.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide2.QtGui import QGuiApplication
from PySide2.QtQml import QQmlComponent, QQmlContext, QQmlEngine

from . import compat, log, paths

SCAN_INTERVAL = 800  # 毫秒

_HOSTS = []


# ======================================================================
# 通用工具
# ======================================================================


try:
    import shiboken2

    def _key(obj):
        try:
            return shiboken2.getCppPointer(obj)[0]
        except Exception:  # noqa: BLE001
            return id(obj)

except Exception:  # noqa: BLE001

    def _key(obj):
        return id(obj)


def _own(obj):
    """把 QQmlComponent.create() 出来的对象转成 Python 所有权，避免被 QML 的 GC 回收。"""
    try:
        import shiboken2

        shiboken2.transferOwnershipToPython(obj)
    except Exception:  # noqa: BLE001
        pass


def _alive(obj):
    """C++ 对象是否还活着（QML 页面可能已被关闭销毁）。"""
    if obj is None:
        return False
    try:
        obj.objectName()
        return True
    except Exception:  # noqa: BLE001
        return False


def _class_of(item):
    try:
        return item.metaObject().className()
    except Exception:  # noqa: BLE001
        return ""


def _has_property(item, name):
    try:
        return item.metaObject().indexOfProperty(name) >= 0
    except Exception:  # noqa: BLE001
        return False


def _children(item):
    try:
        return list(item.childItems())
    except Exception:  # noqa: BLE001
        return []


def _walk(item, depth=0):
    if item is None or depth > 48:
        return
    yield item
    for c in _children(item):
        for x in _walk(c, depth + 1):
            yield x


def _find_first(root, pred):
    for it in _walk(root):
        try:
            if pred(it):
                return it
        except Exception:  # noqa: BLE001
            continue
    return None


# ======================================================================
# 读取「记录」页
# ======================================================================


def _role_id(model, name):
    try:
        roles = model.roleNames()
    except Exception:  # noqa: BLE001
        return None
    for k, v in roles.items():
        try:
            if bytes(v).decode("utf-8", "ignore") == name:
                return int(k)
        except Exception:  # noqa: BLE001
            continue
    return None


def _find_record_model(item, depth=0):
    """在 ResultsTableView 子树里找那个 role 带 resText 的 ListModel。"""
    if item is None or depth > 12:
        return None
    try:
        m = item.property("model")
    except Exception:  # noqa: BLE001
        m = None
    if m is not None and _role_id(m, "resText") is not None:
        return m
    for c in _children(item):
        r = _find_record_model(c, depth + 1)
        if r is not None:
            return r
    return None


def read_record_text(record_item):
    """记录页最后一条非空文本（含用户手动修改过的内容）。"""
    model = _find_record_model(record_item)
    if model is None:
        return ""
    rid = _role_id(model, "resText")
    if rid is None:
        return ""
    try:
        n = model.rowCount()
    except Exception:  # noqa: BLE001
        return ""
    for row in range(n - 1, -1, -1):
        try:
            val = model.data(model.index(row, 0), rid)
        except Exception:  # noqa: BLE001
            continue
        if val is None:
            continue
        s = str(val).strip()
        if s:
            return s
    return ""


def record_timestamp(record_item):
    model = _find_record_model(record_item)
    if model is None:
        return -1.0
    rid = _role_id(model, "timestamp")
    if rid is None:
        return -1.0
    try:
        n = model.rowCount()
        if n <= 0:
            return -1.0
        val = model.data(model.index(n - 1, 0), rid)
        return float(val)
    except Exception:  # noqa: BLE001
        return -1.0


# ======================================================================
# 每个页面一个宿主
# ======================================================================


class EmbedHost(QObject):
    """一个「截图OCR」页面对应的翻译页状态。"""

    openedChanged = Signal()

    def __init__(self, app, page, tab_panel, bar, area, record):
        super().__init__()
        self.app = app
        self.page = page
        self.tab_panel = tab_panel
        self.bar = bar
        self.area = area
        self.record = record
        self._opened = False
        self._button = None
        self._panel = None
        self._ctx = None
        self.tab_index = 2      # 注入完成后按 TabBar.count-1 修正
        self._last_index = -1
        self._pending_text = None

    # ---------------- 生命周期 ----------------

    def is_alive(self):
        return _alive(self.page) and _alive(self.bar) and _alive(self.area)

    def bind_ui(self, button, panel, ctx):
        self._button = button
        self._panel = panel
        self._ctx = ctx

    def keep(self, *objs):
        """持有 QML 组件等对象的 Python 引用，防止被回收。"""
        self._keep = list(objs)

    # ---------------- 属性 ----------------

    def _get_opened(self):
        return self._opened

    opened = Property(bool, _get_opened, notify=openedChanged)

    def _set_opened(self, v):
        v = bool(v)
        if v != self._opened:
            self._opened = v
            self.openedChanged.emit()

    def _get_tab_index(self):
        return self.tab_index

    tabIndex = Property(int, _get_tab_index)

    # ---------------- 数据 ----------------

    def record_text(self):
        try:
            return read_record_text(self.record)
        except Exception:  # noqa: BLE001
            return ""

    def record_ts(self):
        try:
            return record_timestamp(self.record)
        except Exception:  # noqa: BLE001
            return -1.0

    # ---------------- 槽 ----------------

    @Slot(int)
    def onTabChanged(self, index):
        """标签切换（由 Umi 的 TabBar 触发）。"""
        self._note_index_change(index)

        if index == self.tab_index:
            self._set_opened(True)
            text = self._pending_text or self.record_text() or self.app.last_text
            self._pending_text = None
            if text:
                self.app.backend.translate_text(text)
            else:
                self.app.backend.status_message("记录页里还没有可翻译的文本。")
        elif self._opened:
            self._set_opened(False)

        self._last_index = index

    @Slot()
    def close(self):
        """回到「设置」页。"""
        try:
            if self.bar.property("currentIndex") == self.tab_index:
                self.bar.setProperty("currentIndex", 0)
        except Exception:  # noqa: BLE001
            pass

    @Slot()
    def reload(self):
        """只看记录页内容，不翻译。"""
        text = self.record_text() or self.app.last_text
        if text:
            self.app.backend.set_source_text(text)
        else:
            self.app.backend.status_message("记录页里还没有内容。")

    @Slot()
    def openStandalone(self):
        """在独立窗口里打开同一份内容。"""
        text = self.app.backend.sourceText
        self.app.ui.show_window()
        if text:
            self.app.backend.translate_text(text)

    # ---------------- 内部 ----------------

    def _note_index_change(self, index):
        """翻译页不参与 Umi 的"手动切换次数"统计，否则识图后自动切记录页会失效。"""
        involves = (index == self.tab_index) or (self._last_index == self.tab_index)
        if not involves:
            return

        def job():
            try:
                n = self.tab_panel.property("indexChangeNum")
                if isinstance(n, int) and n > 0:
                    self.tab_panel.setProperty("indexChangeNum", n - 1)
            except Exception:  # noqa: BLE001
                pass

        QTimer.singleShot(0, job)

    def _open_panel(self, text=None):
        """切到翻译页（原生切换动画）。"""
        try:
            if self.bar.property("currentIndex") == self.tab_index:
                t = (text or self.record_text() or self.app.last_text or "").strip()
                if t:
                    self.app.backend.translate_text(t)
                return
        except Exception:  # noqa: BLE001
            pass

        self._pending_text = text
        try:
            self.bar.setProperty("currentIndex", self.tab_index)
        except Exception:  # noqa: BLE001
            log.get().exception("切换到翻译页失败")
            self._set_opened(True)

    def open_external(self, text=None):
        """由 OCR 事件 / 热键触发：切到翻译页并翻译给定文本。"""
        self._open_panel(text)


# ======================================================================
# 注入
# ======================================================================


def _menu_of(bar):
    try:
        return bar.parentItem()
    except Exception:  # noqa: BLE001
        return None


def _record_item(tab_panel):
    """从 tabsModel 里按 key 取「记录」页，比按类名找更稳。"""
    try:
        model = tab_panel.property("tabsModel")
    except Exception:  # noqa: BLE001
        model = None
    if model:
        try:
            for entry in model:
                if entry.get("key") == "ocrResult":
                    comp = entry.get("component")
                    if comp is not None:
                        return comp
        except Exception:  # noqa: BLE001
            pass
    return _find_first(tab_panel, lambda it: "ResultsTableView" in _class_of(it))


def _engine_of(item):
    try:
        ctx0 = QQmlEngine.contextForObject(item)
        return ctx0.engine() if ctx0 is not None else None
    except Exception:  # noqa: BLE001
        return None


def _make_component(engine, qml_name, ctx):
    path = os.path.join(paths.QML_DIR, qml_name)
    comp = QQmlComponent(engine, QUrl.fromLocalFile(path))
    if comp.status() == QQmlComponent.Error:
        for err in comp.errors():
            log.get().error("QML 错误 [%s] %s", qml_name, err.toString())
        return None, None
    obj = comp.create(ctx)
    if obj is None:
        log.get().error("创建组件失败: %s", qml_name)
        return None, comp
    _own(obj)
    return obj, comp


def _clone_native_tab(engine, bar):
    """克隆 TabBar 原生标签所用的 delegate，外观和 设置/记录 完全一致。"""
    rep = _find_first(bar, lambda it: "Repeater" in _class_of(it))
    if rep is None:
        return None, None
    try:
        comp = rep.property("delegate")
    except Exception:  # noqa: BLE001
        comp = None
    if comp is None:
        return None, None

    base = None
    try:
        base = QQmlEngine.contextForObject(rep)
    except Exception:  # noqa: BLE001
        base = None
    if base is None:
        return None, None

    dctx = QQmlContext(base)
    dctx.setContextProperty("modelData", {"key": "translate", "title": "翻译"})
    try:
        obj = comp.create(dctx)
    except Exception:  # noqa: BLE001
        log.get().exception("克隆原生标签失败")
        return None, None
    if obj is None:
        return None, None
    _own(obj)
    return obj, comp


def _raise_sibling_pane(tab_panel):
    """
    把与 TabPanel 同一行的"另一个面板"（识图区）抬到上层：
    切换动画中溢出的页面会被它不透明的背景盖住，等效于裁剪。

    返回 (容器, 右栏, 左栏列表)，找不到时返回 None。
    """
    node = tab_panel
    try:
        base_w = float(tab_panel.width())
    except Exception:  # noqa: BLE001
        base_w = 0.0

    try:
        parent = node.parentItem()
    except Exception:  # noqa: BLE001
        parent = None

    while parent is not None:
        try:
            pw = float(parent.width())
        except Exception:  # noqa: BLE001
            pw = 0.0
        sibs = _children(parent)
        if len(sibs) >= 2 and base_w > 0 and pw > base_w * 1.5:
            holder = None
            for s in sibs:
                it = tab_panel
                while it is not None:
                    if _key(it) == _key(s):
                        holder = s
                        break
                    try:
                        it = it.parentItem()
                    except Exception:  # noqa: BLE001
                        it = None
                if holder is not None:
                    break
            if holder is not None:
                lefts = []
                for s in sibs:
                    if _key(s) == _key(holder):
                        continue
                    try:
                        # 只抬高"位于容器左半边"的兄弟（识图区），
                        # 避免把分隔条、拖拽遮罩之类的东西盖到最上层
                        if s.x() + s.width() <= pw * 0.6:
                            s.setZ(2.0)
                            lefts.append(s)
                    except Exception:  # noqa: BLE001
                        pass
                try:
                    holder.setZ(1.0)
                except Exception:  # noqa: BLE001
                    pass
                log.get().info(
                    "已提升兄弟面板层级: %d 个 | 容器 %.0fx%.0f, TabPanel 宽 %.0f",
                    len(lefts),
                    pw,
                    parent.height(),
                    base_w,
                )
                return parent, holder, lefts
        node = parent
        try:
            parent = parent.parentItem()
        except Exception:  # noqa: BLE001
            parent = None
    return None


def inject_page(app, page, host_window):
    tab_panel = _find_first(page, lambda it: "TabPanel" in _class_of(it))
    if tab_panel is None:
        return None

    bar = _find_first(tab_panel, lambda it: "TabBar" in _class_of(it))
    if bar is None:
        return None
    menu = _menu_of(bar)
    if menu is None:
        return None

    area = None
    for c in _children(tab_panel):
        if "SwipeView" in _class_of(c):
            area = c
            break
    if area is None:
        area = _find_first(tab_panel, lambda it: "SwipeView" in _class_of(it))
    if area is None:
        return None

    # 页面切换时会滑到视图外，必须让视图自己裁剪，否则会画到左侧识图区
    try:
        area.setProperty("clip", True)
        ci = area.property("contentItem")
        if ci is not None:
            ci.setProperty("clip", True)
    except Exception:  # noqa: BLE001
        log.get().exception("设置裁剪失败")

    record = _record_item(tab_panel)

    # 标签栏右侧的控制栏（设置页=重置、记录页=滚动…），翻译页要隐藏它
    ctrl_bar = None
    for c in _children(menu):
        if "SwipeView" in _class_of(c):
            ctrl_bar = c
            break

    engine = _engine_of(tab_panel)
    if engine is None:
        return None

    import_path = compat.qml_import_path()
    if import_path:
        try:
            engine.addImportPath(import_path)
        except Exception:  # noqa: BLE001
            pass

    host = EmbedHost(app, page, tab_panel, bar, area, record)

    ctx = QQmlContext(engine.rootContext())
    ctx.setContextProperty("backend", app.backend)
    ctx.setContextProperty("embed", host)
    ctx.setContextProperty("hostWindow", host_window)
    ctx.setContextProperty("anchorBar", bar)
    ctx.setContextProperty("anchorArea", area)
    ctx.setContextProperty("ctrlBar", ctrl_bar)

    # 1) 标签按钮：优先克隆原生 delegate，失败则用自绘的同款按钮
    tab_btn, btn_comp = _clone_native_tab(engine, bar)
    if tab_btn is None:
        log.get().info("未能克隆原生标签，改用内置样式")
        tab_btn, btn_comp = _make_component(engine, "EmbedTabButton.qml", ctx)
    if tab_btn is None:
        return None

    # 2) 翻译页
    panel, panel_comp = _make_component(engine, "EmbedPanel.qml", ctx)
    if panel is None:
        return None

    # 3) 交给 Umi 的 Container 控制器挂上去
    ctx.setContextProperty("___tab", tab_btn)
    ctx.setContextProperty("___page", panel)
    installer, inst_comp = _make_component(engine, "EmbedInstaller.qml", ctx)
    if installer is not None:
        try:
            installer.setParentItem(menu)
        except Exception:  # noqa: BLE001
            pass

    try:
        count = int(bar.property("count"))
    except Exception:  # noqa: BLE001
        count = 0
    if count >= 3:
        host.tab_index = count - 1
    else:
        log.get().warning("标签注入可能失败：TabBar.count=%s", count)

    host.bind_ui(tab_btn, panel, ctx)
    host.keep(btn_comp, panel_comp, inst_comp, installer)

    info = _raise_sibling_pane(tab_panel)
    if info is not None:
        parent, _holder, lefts = info
        if lefts:
            ctx.setContextProperty("paneTarget", lefts[0])
            cover, cover_comp = _make_component(engine, "PaneCover.qml", ctx)
            if cover is not None:
                try:
                    cover.setParentItem(parent)
                    cover.setZ(1.5)
                    host.keep(cover_comp, cover)
                except Exception:  # noqa: BLE001
                    log.get().exception("挂载遮挡层失败")

    return host


# ======================================================================
# 扫描 / 注册表
# ======================================================================


def live_hosts():
    global _HOSTS
    _HOSTS = [h for h in _HOSTS if h.is_alive()]
    return _HOSTS


def active_host():
    hosts = live_hosts()
    if not hosts:
        return None
    best = None
    best_ts = -2.0
    for h in hosts:
        ts = h.record_ts()
        if ts > best_ts:
            best_ts = ts
            best = h
    return best if best is not None else hosts[-1]


def active_text():
    h = active_host()
    return h.record_text() if h is not None else ""


def scan(app):
    """找所有 截图OCR 页面，缺的就注入。"""
    try:
        windows = QGuiApplication.allWindows()
    except Exception:  # noqa: BLE001
        return
    for win in windows:
        try:
            content = win.contentItem()
        except Exception:  # noqa: BLE001
            continue
        if content is None:
            continue
        try:
            is_main = _has_property(win, "theme")
        except Exception:  # noqa: BLE001
            is_main = False
        if not is_main:
            continue  # 不是 Umi 主窗口（例如我们自己的 QQuickView）

        for page in [it for it in _walk(content) if _has_property(it, "msnState")]:
            if any(_key(h.page) == _key(page) for h in live_hosts()):
                continue
            try:
                host = inject_page(app, page, win)
            except Exception:  # noqa: BLE001
                log.get().exception("注入翻译标签失败")
                host = None
            if host is not None:
                _HOSTS.append(host)
                try:
                    log.get().info(
                        "已注入「翻译」标签（%s）: tab=%s页 view=%s页 tabIndex=%s",
                        _class_of(page),
                        host.bar.property("count"),
                        host.area.property("count"),
                        host.tab_index,
                    )
                except Exception:  # noqa: BLE001
                    log.get().info("已注入「翻译」标签（%s）", _class_of(page))
            else:
                log.get().warning("注入失败：未找到 TabPanel/TabBar/SwipeView")


class Scanner(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._timer = None

    def start(self):
        if self._timer is not None:
            return
        self._timer = QTimer()
        self._timer.setInterval(SCAN_INTERVAL)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

    def _tick(self):
        try:
            scan(self.app)
        except Exception:  # noqa: BLE001
            log.get().exception("扫描截图OCR页面失败")
