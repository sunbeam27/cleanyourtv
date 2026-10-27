# CAN F55：API 21 本地移植交付与试装指南

这是 CleanYourTV 的独立本地实验适配，尚未在 CAN F55 真机安装或验证。上游基线为
`57733360177173c880a023380a864114a03feb25`，来源为
[Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv)。上游官方版本的最低版本仍为
API 26；本适配不能作为官方支持 CAN F55 的证明。

## 设备依据与本轮边界

历史诊断记录称设备为 CAN 超能电视 F55，Android 5.0.1 / API 21，未列出 leanback feature；
原厂 HOME 包为 `cn.cibntv.ott`，第三方 HOME 曾被原厂接管。TVBox 包为
`com.github.tvbox.osc.jun`，历史记录有 LAUNCHER 和 LEANBACK_LAUNCHER 入口，用户确认过开机进入
TVBox。本轮未重新验证 ADB 连接、root、硬件 ABI、包是否仍安装、实际启动组件或固件行为。

最初交付阶段仅做本地源码适配、构建和静态/JVM 检查；用户随后另行授权在自己的 GitHub fork 中
保存适配并通过 Actions 构建，实际仓库、提交和运行结果见最终交付材料。这不包含真机操作授权。
没有运行仓库的 debloat/install/restore 一键脚本，
没有连接、安装或修改电视，没有停用或删除原厂包，没有改变默认 HOME、TVBox 自启动配置、
调试安全设置、无障碍服务或通知访问权限。后续安装新 HOME 应用时，固件可能重新显示默认桌面
选择器；本适配没有强制设置默认桌面的代码或操作，亦不保证固件不会重新接管 HOME。

## 交付身份与源码变化

| 项目 | 本地适配 |
| --- | --- |
| Gradle flavor | `canF55`；`standard` 保留上游 API 26 下限 |
| 包名 | `com.gathin.tvhome.canf55`（构建时不传 `launcherApplicationId`） |
| 启动 Activity | `com.gathin.tvhome.MainActivity` |
| 最低 SDK | API 21，仅适用于 `canF55` flavor |
| 目标 SDK / 编译 SDK | 34 / 34 |
| 显示名称 | `CleanYourTV F55` |
| APK 路径、大小、SHA-256、签名检查 | 见最终交付 manifest；此处不预填构建结果 |
| 真机状态 | 未安装、未验证 |

主要适配：

- 保留现有 HOME / DEFAULT 和 LEANBACK_LAUNCHER，仅 F55 flavor 追加普通 Android LAUNCHER
  入口；标准变体保留上游入口。leanback feature 保持非必需，Activity 类名仍为
  `com.gathin.tvhome.MainActivity`，不随 F55 应用包名后缀变化。
- 启用原有应用库：它合并普通 LAUNCHER 和 LEANBACK_LAUNCHER，同包优先电视入口并去重。
  F55 专用配置把 TVBox 放在 dock 第一位、原厂桌面放在第二位，两者也预置为 Home 快捷方式。
  未安装或不能解析的应用会跳过，不伪造可用入口。
- 已选快捷方式先找 LEANBACK、再找普通 LAUNCHER，最后允许导出的 HOME 入口，覆盖原厂桌面
  只有 HOME filter 的情况。该入口只在用户点选时启动，不改变默认 HOME。
- F55 使用系统 sans-serif 字体族，保留原界面的轻/常规/中等字重层次；API 21 不加载 `res/font`。
  默认 reduced motion，关闭模块卡片，不预设未经验证的 tuner/HDMI 厂商启动包。
- 高版本 framework API 使用版本检查/低版本替代；Java 库 API 使用 core library desugaring。
  详细 API 21 审计、检查通过/失败/未执行项目见最终交付材料。

这些调整保留已有网格、方向键、焦点高亮和应用库交互。字形、动画、网络状态精度等降级以
最终审计记录为准；编译通过不能证明 CAN 固件、遥控器、GPU 或 HDMI 输入兼容。

## API 21 明确降级

| 功能与原 API 下限 | API 21 行为与限制 |
| --- | --- |
| 输入源自定义名称与隐藏状态，API 24 | 不调用 `loadCustomLabel()` / `isHidden()`。名称退回系统输入名称、设备名称或现有配置；无法读取系统设置中的隐藏标志，因此可能列出固件隐藏的直通输入。原厂输入源菜单仍是核对和使用输入源的可靠路径。 |
| 网络互联网验证状态，API 23 | 可显示连接状态，但不把缺少 `NET_CAPABILITY_VALIDATED` 当成已验证互联网，也不据此误报“无互联网”。API 21 的网络状态颜色回到普通色；连接 Wi-Fi/以太网不等于互联网可用。 |
| 每次开机只打开一次指定应用，`BOOT_COUNT` | 读不到计数时返回未知值并跳过启动选择，不用进程重启猜测一次新开机。本 flavor 默认关闭这一选择，也不改变已有 TVBox 开机进入方式。 |
| 自定义按键动作 `mute`，API 23 | API 23 以下不发送 `ADJUST_TOGGLE_MUTE`；该自定义映射跳过静音切换。电视原有遥控静音键由固件处理。本阶段不启用按键助手。 |
| 待机时退出/唤醒重挂无障碍助手，API 24 | API 24 以下关闭该可选待机 helper，不调用 `disableSelf()` 或依赖 direct-boot/unlocked API；本阶段不启用任何无障碍或通知监听服务。 |
| 资源字体加载，API 26 | F55 覆写为系统 `sans-serif` 字体族；运行代码也在低于 API 26 时回退系统字体。保留字重层次，实际字形与上游 Outfit 字体不同。 |
| `java.time`、`java.util.function` 与部分 Java 集合 API | 开启 core library desugaring，以 `desugar_jdk_libs:2.0.4` 提供低版本库兼容；Java 源码级别仍为 17。代价是 APK 大小增加，最终依赖、构建及 lint 结果见交付材料。 |
| 原厂对 HOME 的接管 | 没有绕过。仅注册可选 HOME 并支持普通应用入口；不设置默认 HOME、不停用原厂、不改按键服务或 TVBox 自启动。显式普通启动成功不能证明 HOME 键与开机后会进入本桌面。 |

以上是源码中的防护和降级设计，尚无本台电视的运行证据。API 21 JVM/静态检查不能替代真机
启动、真实遥控器、待机唤醒或固件行为验证。

## 本地重建

使用官方来源的 JDK 17、Android SDK platform 34 / build-tools 34.0.0、仓库 Gradle wrapper。
依赖下载需要网络；若提示安装组件或接受新的 SDK 条款，先报告并等待确认，不自动接受。
不要使用 `build-and-install.*`，它会包含超出本轮授权的设备操作。

在 `launcher` 目录运行纯构建任务：

```powershell
.\gradlew.bat --no-daemon testCanF55ReleaseUnitTest lintCanF55Release assembleCanF55Release
```

在仓库根目录可单独运行不接触电视的源码配置验收检查，覆盖 HOME/两种应用入口、TVBox 与原厂
快捷方式、没有默认选择开机跳转、系统字体：

```powershell
python -m unittest discover -s tests -p test_can_f55_port.py -v
```

默认输出位于 `launcher/app/build/outputs/apk/canF55/release/`。本地 release 沿用上游的 debug
签名配置，不是官方生产签名；实际签名证书摘要以最终 APK 检查为准。以后覆盖安装需要相同签名，
不要通过卸载原厂或其他包来绕过签名不匹配。

## 后续只读诊断清单（尚未执行）

以下所有电视命令仅为后续取得授权后的人工操作清单，不代表本轮已运行。先在普通终端核对设备，
只使用明确选择的序列号，不自动扫描网络、不猜 IP、不运行 `su`。不要把占位符直接粘贴执行。

```powershell
adb version
adb devices -l
# 将 SERIAL 替换为已核对的目标序列号；多台设备时始终保留 -s。
adb -s SERIAL get-state
adb -s SERIAL shell id
adb -s SERIAL shell getprop ro.product.model
adb -s SERIAL shell getprop ro.build.version.release
adb -s SERIAL shell getprop ro.build.version.sdk
adb -s SERIAL shell getprop ro.build.fingerprint
adb -s SERIAL shell getprop ro.product.cpu.abi
adb -s SERIAL shell getprop ro.product.cpu.abi2
adb -s SERIAL shell getprop ro.product.cpu.abilist
adb -s SERIAL shell pm list features
adb -s SERIAL shell pm list packages -f
adb -s SERIAL shell pm list packages -d
adb -s SERIAL shell dumpsys package cn.cibntv.ott
adb -s SERIAL shell dumpsys package com.github.tvbox.osc.jun
adb -s SERIAL shell dumpsys activity activities
adb -s SERIAL shell settings get secure enabled_accessibility_services
adb -s SERIAL shell settings get secure accessibility_enabled
adb -s SERIAL shell wm size
adb -s SERIAL shell wm density
```

`id` 只显示当前 ADB shell 的身份，并不证明 `su` 可用。空的 `abilist` 也不等于没有 ABI；结合
`cpu.abi` 与 `cpu.abi2` 判断。API 21 不使用较新的 `cmd package set-home-activity`、
`cmd package resolve-activity` 等命令。用包的 `dumpsys` 输出人工核对实际 MAIN、HOME、LAUNCHER、
LEANBACK_LAUNCHER 组件与导出情况；不要凭类名猜原厂启动 Activity，更不要启动工厂/测试包。

包清单、固件信息、日志和截图只保存在本地诊断目录；分享前移除序列号、IP/MAC、Android ID、
Wi-Fi 名称、账户和其他家庭资料。输出可能含个人信息，不把完整 `dumpsys`/`getprop` 上传到公开仓库。

## 后续手工试装（必须另行确认）

试装前确认：只读诊断确为目标 F55 / API 21；原厂与 TVBox 保持启用；现有 TVBox 开机方式已记录；
APK 的包名、最低 SDK、SHA-256 和签名与最终交付 manifest 一致；遥控器可返回原有应用。
如检测到其他系统版本或安装验证失败，先停下记录原始报错，不循环重试或绕过校验。

取得真机试装授权后，人工逐条执行，并把 `APK` 换成已核对的 APK 绝对路径：

```powershell
adb -s SERIAL install -r "APK"
adb -s SERIAL shell am start -n com.gathin.tvhome.canf55/com.gathin.tvhome.MainActivity
```

先通过显式 Activity 作为普通应用打开。不要选择“始终”设为 HOME，不执行默认桌面设置、不停用
`cn.cibntv.ott`、不修改 TVBox 自启动，不开启无障碍/通知监听，不授予 WRITE_SECURE_SETTINGS，
不运行仓库一键脚本。API 21 的普通安装权限提示也应人工审阅。

若安装器提示签名不匹配，先核对是否已有同包测试版本与签名，交还确认，不擅自卸载。若普通启动
成功但 HOME 被原厂接管，记录该现象；本阶段不实施抢占 HOME 或固件绕过方案。

## 遥控器与运行手工测试矩阵（全部待执行）

| 场景 | 操作 | 记录与通过条件 |
| --- | --- | --- |
| 首次打开 | 显式启动 Activity | 无崩溃/黑屏；中文可读；初始焦点可见 |
| dock 与网格边界 | 逐个按左/右/上/下，覆盖四边与不足一行 | 焦点始终可见，无越界、空槽困住或异常跳转 |
| 顶部按钮往返 | 网格上移到顶部，再下移 | 焦点能返回应用；Settings/网络页可返回 |
| TVBox 入口 | 在第一位 TVBox 按 OK，再用返回键回来 | 打开正确 TVBox，无重复 tile；回到合理焦点位置 |
| 原厂入口 | 先核对其可解析组件，再点原厂 tile | 打开原厂桌面，不启动工厂/测试页；可返回实验桌面 |
| 普通应用库 | 打开应用库，左右/上下/OK/长按/返回 | 普通和电视应用可见，同包不重复；选择和退出可用 |
| 应用缺失/停用 | 只观察当前诊断结果，不为测试停用包 | 不显示失效预置项；没有可用 app 时仍能操作顶部/应用库 |
| 长按与菜单 | 遥控器长按 OK；有 MENU 键时按 MENU | 行为符合现有配置；返回键关闭菜单、不丢焦点 |
| 多次切换 | TVBox/原厂/其他普通应用往返数次 | 不崩溃，焦点和图标正常恢复，未强制改变 HOME |
| HOME 键 | 实按遥控器 HOME | 记录固件实际去向；本阶段允许回到原有 HOME，不抢占 |
| 输入源 | 人工使用原厂输入源菜单，核对 HDMI/电视功能 | 原厂输入/声音/遥控仍工作；不假定第三方输入菜单可用 |
| 待机唤醒 | 经确认后人工待机再唤醒 | 原有启动方式可恢复；无异常接管或黑屏 |
| 重启 | 仅在单独确认后人工重启 | 原有 TVBox 开机流程保持；ADB 是否恢复单独记录 |
| 低内存/长时间运行 | 正常看节目后返回，观察数小时 | 无持续卡顿或内存崩溃；不作无证据的性能结论 |

注入的 ADB 按键不能替代真实遥控器；本轮没有启用任何按键无障碍助手。记录电视型号、固件、测试
时间、具体按键和可复现步骤。若崩溃，先保存本地 logcat 与截图，再停止该轮试验。

## 后续回退（相关设备动作也需另行授权）

1. 先按遥控器 BACK，或在原有应用列表中手动打开 TVBox/原厂桌面。不要改默认 HOME。
2. 若需 ADB 恢复前台，先从只读诊断核对 TVBox 或原厂的导出启动组件；得到授权后才用
   `adb -s SERIAL shell am start -n VERIFIED_COMPONENT`，其中 `VERIFIED_COMPONENT` 必须是真实核对
   的 `包名/Activity`，不能猜测。
3. 如实验桌面反复异常，得到授权后可仅强停本测试包：

   ```powershell
   adb -s SERIAL shell am force-stop com.gathin.tvhome.canf55
   ```

4. 确认原有桌面和 TVBox 正常后，如用户明确同意删除这个用户安装的实验应用，优先通过系统
   应用管理中名称与包名核对后卸载。只有再次确认目标确为本实验包时，才可考虑：

   ```powershell
   adb -s SERIAL uninstall com.gathin.tvhome.canf55
   ```

   这只用于单独安装的本实验包，不能替换为原厂、TVBox 或任何系统包；卸载会删除实验桌面的
   本地设置。没有改过原厂/TVBox的启用状态与启动配置，因此不要运行批量 restore 脚本。

若先前已有其他任务改过 HOME、无障碍或开机配置，不套用“未更改所以无需恢复”的假设；先提供
真实诊断与变更记录，另行确认恢复方案。本指南中的设备操作目前均未执行。
