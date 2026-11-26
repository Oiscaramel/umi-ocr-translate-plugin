import QtQuick 2.15

// 翻译窗口（无边框、可拖动、可缩放、可选置顶）
Item {
    id: root
    width: 760
    height: 420
    focus: true

    property bool settingsOpen: false
    property real dragX: 0
    property real dragY: 0

    Keys.onPressed: {
        if (event.key === Qt.Key_Escape) {
            backend.closeWindow()
            event.accepted = true
        }
    }

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 12
        color: "#fbfcfd"
        border.width: 1
        border.color: "#cfd6df"

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: 11
            color: "transparent"
            border.width: 1
            border.color: "#ffffff"
        }
    }

    // ==================== 标题栏 ====================
    Item {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 44

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onPressed: {
                root.dragX = mouse.x
                root.dragY = mouse.y
            }
            onPositionChanged: {
                backend.moveBy(Math.round(mouse.x - root.dragX), Math.round(mouse.y - root.dragY))
            }
        }

        Rectangle {
            id: logo
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            width: 26
            height: 26
            radius: 7
            color: "#1f6feb"

            Text {
                anchors.centerIn: parent
                text: "译"
                color: "#ffffff"
                font.pixelSize: 14
                font.bold: true
                font.family: "Microsoft YaHei"
            }
        }

        Column {
            anchors.left: logo.right
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0

            Text {
                text: "本地翻译"
                color: "#1f2328"
                font.pixelSize: 13
                font.bold: true
                font.family: "Microsoft YaHei"
            }
            Text {
                text: "NLLB-200 · 离线"
                color: "#8c959f"
                font.pixelSize: 10
                font.family: "Microsoft YaHei"
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 5

            Btn {
                text: "自动"
                active: backend.direction === "auto"
                onClicked: backend.setDirection("auto")
            }
            Btn {
                text: "中 → 英"
                active: backend.direction === "zh-en"
                onClicked: backend.setDirection("zh-en")
            }
            Btn {
                text: "英 → 中"
                active: backend.direction === "en-zh"
                onClicked: backend.setDirection("en-zh")
            }
            Item {
                width: 4
                height: 1
            }
            Btn {
                text: backend.pinned ? "已置顶" : "置顶"
                active: backend.pinned
                onClicked: backend.togglePin()
            }
            Btn {
                text: "设置"
                active: root.settingsOpen
                onClicked: root.settingsOpen = !root.settingsOpen
            }
            Btn {
                text: "✕"
                onClicked: backend.closeWindow()
            }
        }
    }

    Rectangle {
        id: sep1
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: "#e6e9ee"
    }

    // ==================== 主体 ====================
    Item {
        id: body
        anchors.top: sep1.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: footer.top

        Row {
            id: row
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            // ---------- 原文 ----------
            Rectangle {
                width: (row.width - row.spacing) / 2
                height: row.height
                radius: 8
                color: "#ffffff"
                border.width: 1
                border.color: "#e2e7ee"

                Item {
                    id: leftHead
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 30

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: "原文"
                        color: "#57606a"
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "Microsoft YaHei"
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 5

                        Btn {
                            text: "复制"
                            onClicked: backend.copySource()
                        }
                        Btn {
                            text: "清空"
                            onClicked: backend.sourceText = ""
                        }
                    }
                }

                Flickable {
                    id: leftFlick
                    anchors.top: leftHead.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    anchors.bottomMargin: 8
                    contentWidth: width
                    contentHeight: srcEdit.contentHeight + 4
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    TextEdit {
                        id: srcEdit
                        width: leftFlick.width
                        text: backend.sourceText
                        wrapMode: TextEdit.Wrap
                        textFormat: TextEdit.PlainText
                        selectByMouse: true
                        selectByKeyboard: true
                        color: "#1f2328"
                        selectionColor: "#b6d4fe"
                        selectedTextColor: "#1f2328"
                        font.pixelSize: 13
                        font.family: "Microsoft YaHei"
                        onTextChanged: {
                            if (text !== backend.sourceText)
                                backend.sourceText = text
                        }
                    }

                    Text {
                        visible: srcEdit.text.length === 0
                        text: "截图识别后自动填入，也可直接粘贴文本。"
                        color: "#9aa4af"
                        font.pixelSize: 12
                        font.family: "Microsoft YaHei"
                        width: leftFlick.width
                        wrapMode: Text.Wrap
                    }
                }
            }

            // ---------- 译文 ----------
            Rectangle {
                width: (row.width - row.spacing) / 2
                height: row.height
                radius: 8
                color: "#f7f9fc"
                border.width: 1
                border.color: "#e2e7ee"

                Item {
                    id: rightHead
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 30

                    Text {
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        text: "译文"
                        color: "#57606a"
                        font.pixelSize: 11
                        font.bold: true
                        font.family: "Microsoft YaHei"
                    }

                    Row {
                        anchors.right: parent.right
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 5

                        Btn {
                            text: "复制译文"
                            onClicked: backend.copyTarget()
                        }
                    }
                }

                Flickable {
                    id: rightFlick
                    anchors.top: rightHead.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.leftMargin: 10
                    anchors.rightMargin: 8
                    anchors.bottomMargin: 8
                    contentWidth: width
                    contentHeight: dstEdit.contentHeight + 4
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds

                    TextEdit {
                        id: dstEdit
                        width: rightFlick.width
                        text: backend.targetText
                        readOnly: true
                        wrapMode: TextEdit.Wrap
                        textFormat: TextEdit.PlainText
                        selectByMouse: true
                        selectByKeyboard: true
                        color: "#1f2328"
                        selectionColor: "#b6d4fe"
                        selectedTextColor: "#1f2328"
                        font.pixelSize: 13
                        font.family: "Microsoft YaHei"
                    }

                    Text {
                        visible: dstEdit.text.length === 0
                        text: "点「翻译」或按 Ctrl+Alt+T 翻译最近一次识图结果。"
                        color: "#9aa4af"
                        font.pixelSize: 12
                        font.family: "Microsoft YaHei"
                        width: rightFlick.width
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    // ==================== 底部状态栏 ====================
    Item {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 42

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: "#e6e9ee"
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: actions.left
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: backend.statusText
            color: backend.busy ? "#1f6feb" : "#57606a"
            font.pixelSize: 11
            font.family: "Microsoft YaHei"
            elide: Text.ElideRight
        }

        Row {
            id: actions
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Btn {
                text: backend.lineMode === "line" ? "逐行" : "段落"
                onClicked: backend.toggleLineMode()
            }
            Btn {
                text: backend.autoTranslate ? "自动翻译：开" : "自动翻译：关"
                onClicked: backend.toggleAutoTranslate()
            }
            Btn {
                text: backend.busy ? "翻译中…" : "翻译"
                primary: true
                enabled: !backend.busy
                onClicked: backend.requestTranslate()
            }
        }
    }

    Rectangle {
        id: busyBar
        visible: backend.busy
        anchors.bottom: footer.top
        width: root.width / 3
        height: 2
        color: "#1f6feb"

        NumberAnimation on x {
            running: backend.busy
            from: -root.width / 3
            to: root.width
            duration: 1300
            loops: Animation.Infinite
        }
    }

    // ==================== 设置浮层 ====================
    Rectangle {
        id: settings
        visible: root.settingsOpen
        anchors.top: header.bottom
        anchors.right: parent.right
        anchors.topMargin: 6
        anchors.rightMargin: 10
        width: 300
        height: settingsCol.height + 20
        radius: 8
        color: "#ffffff"
        border.width: 1
        border.color: "#d6dce5"
        z: 20

        Column {
            id: settingsCol
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 10
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 6

            Text {
                text: "翻译服务"
                color: "#1f2328"
                font.pixelSize: 12
                font.bold: true
                font.family: "Microsoft YaHei"
            }
            Text {
                width: parent.width
                text: backend.serviceText
                color: "#57606a"
                font.pixelSize: 11
                wrapMode: Text.Wrap
                font.family: "Microsoft YaHei"
            }
            Row {
                spacing: 5
                Btn {
                    text: "刷新"
                    onClicked: backend.refreshService()
                }
                Btn {
                    text: "重启服务"
                    onClicked: backend.restartService()
                }
                Btn {
                    text: "停止"
                    onClicked: backend.stopService()
                }
            }
            Btn {
                text: "打开日志目录"
                onClicked: backend.openLogs()
            }
            Text {
                width: parent.width
                text: "热键、悬浮按钮、端口等可在插件目录 config.json 中修改。"
                color: "#8c959f"
                font.pixelSize: 10
                wrapMode: Text.Wrap
                font.family: "Microsoft YaHei"
            }
        }
    }

    // ==================== 边缘缩放 ====================
    Item {
        id: resizeLayer
        anchors.fill: parent
        z: 200

        MouseArea {
            width: 6
            height: parent.height
            anchors.left: parent.left
            cursorShape: Qt.SizeHorCursor
            onPressed: backend.startResize("left")
        }
        MouseArea {
            width: 6
            height: parent.height
            anchors.right: parent.right
            cursorShape: Qt.SizeHorCursor
            onPressed: backend.startResize("right")
        }
        MouseArea {
            width: parent.width
            height: 6
            anchors.top: parent.top
            cursorShape: Qt.SizeVerCursor
            onPressed: backend.startResize("top")
        }
        MouseArea {
            width: parent.width
            height: 6
            anchors.bottom: parent.bottom
            cursorShape: Qt.SizeVerCursor
            onPressed: backend.startResize("bottom")
        }
        MouseArea {
            width: 12
            height: 12
            anchors.left: parent.left
            anchors.top: parent.top
            cursorShape: Qt.SizeFDiagCursor
            onPressed: backend.startResize("topleft")
        }
        MouseArea {
            width: 12
            height: 12
            anchors.right: parent.right
            anchors.top: parent.top
            cursorShape: Qt.SizeBDiagCursor
            onPressed: backend.startResize("topright")
        }
        MouseArea {
            width: 12
            height: 12
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            cursorShape: Qt.SizeBDiagCursor
            onPressed: backend.startResize("bottomleft")
        }
        MouseArea {
            width: 12
            height: 12
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            cursorShape: Qt.SizeFDiagCursor
            onPressed: backend.startResize("bottomright")
        }
    }
}
