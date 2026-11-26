# Umi-OCR 本地离线翻译插件

适用于 **Umi-OCR v2.1.5（Windows x64）**。给 Umi-OCR 加一个**完全离线**的中英互译功能：
截图 OCR 页面右侧「设置」「记录」旁边会多一个 **「翻译」** 标签，
点一下就把**记录页最后一条**识别结果翻译出来。

- 翻译引擎：**NLLB-200-distilled-600M**（CTranslate2 int8，纯 CPU 推理）
- 不需要联网、不需要 API Key、不修改 Umi-OCR 任何文件
- 安装 = 把 `umi_local_translate` 整个文件夹放进 `UmiOCR-data/plugins/`
- 卸载 = 删除该文件夹

---

## 1. 安装

1. 关闭 Umi-OCR。
2. 把整个 `umi_local_translate` 文件夹复制到：

   ```
   <Umi-OCR 安装目录>\UmiOCR-data\plugins\umi_local_translate
   ```

   复制完成后目录结构应为：

   ```
   UmiOCR-data\plugins\umi_local_translate\
   ├─ __init__.py
   ├─ core\
   ├─ qml\
   ├─ service\
   ├─ runtime\        ← 内置 Python 3.12 + 依赖
   ├─ models\         ← NLLB 模型（约 650MB）
   ├─ tools\
   └─ config.json
   ```

3. 启动 Umi-OCR。日志 `plugins\umi_local_translate\logs\plugin.log` 里会出现
   `已注入「翻译」标签`。
4. 打开一个「截图 OCR」标签页，右侧标签栏就是 `设置 | 记录 | 翻译`。

> 首次翻译会启动翻译服务并加载模型（约 3–6 秒），之后每次翻译约 0.3–1 秒。
> 服务空闲 15 分钟后自动退出，下次点击会重新拉起。

## 2. 怎么用

| 操作 | 效果 |
|---|---|
| 点「翻译」标签 | 读取**记录页最后一条**内容并翻译 |
| 页里「从记录刷新」 | 重新读取记录页内容（不翻译） |
| 页里「翻译」 | 翻译当前「原文」框里的内容（可直接编辑） |
| 点「设置」/「记录」 | 切回对应页面（原生标签切换动画） |
| 「中 → 英 / 英 → 中 / 自动」 | 切换翻译方向，自动记住 |
| 「段落 / 逐行」 | 段落模式译文更通顺；逐行模式保留每行对应关系 |
| 「自动翻译：开」 | 每次 OCR 完成自动切到翻译页并翻译（默认关闭） |
| 「⚙」 | 打开设置：独立窗口热键开关 + 热键自定义 |
| 「独立窗口」 | 把当前内容放进大窗口里看（也可用热键唤起） |

### 关于「记录页的内容」

翻译时**读的是记录页里的实际内容**，不是 OCR 原始事件，所以：

- 你在记录页里**手动改过的文字**会被正确识别
- 记录页有多条时，取**最后一条**（即最近一次识别）
- 记录页被清空时，退回 OCR 事件里缓存的文本

## 3. 独立窗口热键

翻译页里点「⚙」：

```
独立窗口热键
[热键：开]  [ ctrl+alt+t      ]  [应用]
例：ctrl+alt+t、ctrl+shift+f2
```

- 按热键会弹出独立窗口，并翻译记录页最后一条
- 「应用」后立即生效（不用重启 Umi）
- 热键被占用/格式错误时，翻译页底部状态栏会提示原因
- 关掉开关即不再注册热键

## 4. 配置

编辑 `plugins\umi_local_translate\config.json`，重启 Umi-OCR 生效：

```jsonc
{
  "enabled": true,          // 总开关
  "auto_translate": false,  // OCR 后自动翻译
  "direction": "auto",      // auto | zh-en | en-zh
  "embed_button": true,     // 在截图OCR页注入「翻译」标签
  "hotkey": "ctrl+alt+t",   // 独立窗口热键
  "hotkey_enabled": true,   // 热键开关
  "preload": false,         // 启动后立即预热服务（占用约 700MB 内存）
  "line_mode": "block",     // block（段落）| line（逐行）
  "service": {
    "port": 17321,          // 起始端口，被占用时自动往后找
    "idle_timeout": 900,    // 空闲多少秒退出服务
    "beam_size": 4,         // 1 最快，4 质量更好
    "threads": 0,           // 0 = 自动（CPU 核数 - 4，最多 12）
    "compute_type": "int8", // int8 | int8_float32 | float32
    "start_timeout": 90
  },
  "window": { "width": 760, "height": 420, "always_on_top": false }
}
```

独立窗口的行为（尺寸 / 位置 / 置顶）在窗口标题栏里调整，关闭时自动写回 `window`。

## 5. 换电脑 / 换目录

**整个文件夹可以直接拷贝**到另一台同版本 Umi-OCR 上使用，不需要装 Python、不需要 uv、不需要联网。

原因：运行时是自包含的

- `runtime/python` 是可重定位的 CPython 3.12 standalone（不是 venv，没有 `pyvenv.cfg`，没有写死路径的启动器）
- `runtime/site-packages` 是用 `uv pip install --target` 装的，里面没有任何绝对路径
- 代码里所有路径都相对插件目录计算

迁移前可以自查一遍：

```powershell
cd <插件目录>
.\runtime\python\python.exe tools\verify_portable.py
```

加 `--relocate` 会把整个插件复制到临时目录再真实翻译一次：

```powershell
.\runtime\python\python.exe tools\verify_portable.py --relocate
```

要求：64 位 Windows + 支持 AVX2 的 CPU（2013 年后的处理器基本都支持）。

## 6. 故障排查

**看不到「翻译」标签**

- 只能出现在「截图 OCR」页面；其它页面（批量 OCR、二维码）没有
- 看 `logs\plugin.log` 里有没有 `已注入「翻译」标签`
- 若出现 `注入失败：未找到 TabPanel/TabBar/SwipeView`，说明 Umi 版本改了页面结构，
  把 `config.json` 里 `embed_button` 设为 `false` 可关掉注入（热键仍可用）

**点「翻译」后一直"正在加载翻译模型…"**

- 模型加载失败会在面板底部显示原因，详细堆栈见 `logs\service.log`
- 不要移动或改名 `models\nllb-200-distilled-600M-int8`

**提示"运行时缺失 / 模型缺失"**

- 说明文件夹没复制完整，重新完整复制一次（`runtime` 与 `models` 都必须存在）

**热键无效**

- 可能被其它软件占用；在面板「⚙」里换一个，例如 `ctrl+shift+t`

**想用 GPU 加速**

- 需要额外安装 CUDA/cuDNN 版本的 ctranslate2，本包只带 CPU 版；CPU int8 已经够用

**升级 Umi-OCR 之后**

- 如果安装在新的目录，把插件文件夹重新复制一次即可（配置和模型都在文件夹内）

## 7. 卸载

关闭 Umi-OCR，删除 `UmiOCR-data\plugins\umi_local_translate` 整个文件夹。
如果翻译服务还在运行，任务管理器结束命令行含 `server.py` 的 `pythonw.exe` 即可。

## 8. 许可与说明

- 本插件是对 Umi-OCR v2.1.5 的**运行时扩展**（在 QML 场景里注入一个标签和一个面板），
  不修改 Umi-OCR 源码；若未来版本改动页面结构，可能需要更新插件。
- 本项目在 AI 编程助手（OpenCode + DeepSeek）协助下完成，
  详见仓库根目录 README 的「AI 使用说明」一节。
- 翻译模型 `nllb-200-distilled-600M` 由 Meta 发布，许可证 **CC-BY-NC 4.0**（非商用）。
  个人使用没有问题；如需商用或再分发，请替换为 OPUS-MT 等许可更宽松的模型。
- 运行时依赖：`ctranslate2`(MIT) / `tokenizers`(Apache-2.0) / `numpy`(BSD)。
