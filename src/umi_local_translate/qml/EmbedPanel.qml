import QtQuick 2.15

// 覆盖在「记录」结果区上的内嵌翻译面板
Item {
    id: root

    width: anchorArea ? anchorArea.width : 400
    height: anchorArea ? anchorArea.height : 300

    property bool settingsOpen: false

    // 标签切换由 Umi 的 TabBar 触发，这里只做转发
    Connections {
        target: anchorBar
        onCurrentIndexChanged: {
            if (anchorBar.currentIndex !== embed.tabIndex)
                root.settingsOpen = false
            embed.onTabChanged(anchorBar.currentIndex)
        }
    }

    // 翻译页激活时，隐藏标签栏右侧那条"页面自带控制栏"（重置/滚动…）
    Connections {
        target: embed
        onOpenedChanged: if (ctrlBar) ctrlBar.visible = !embed.opened
    }

    Rectangle {
        anchors.fill: parent
        color: "#fbfcfd"
    }

    // ==================== 顶栏 ====================
    Item {
        id: toolbar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 34

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            TBtn {
                text: "自动"
                active: backend.direction === "auto"
                onClicked: backend.setDirection("auto")
            }
            TBtn {
                text: "中 → 英"
                active: backend.direction === "zh-en"
                onClicked: backend.setDirection("zh-en")
            }
            TBtn {
                text: "英 → 中"
                active: backend.direction === "en-zh"
                onClicked: backend.setDirection("en-zh")
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            TBtn {
                text: backend.lineMode === "line" ? "逐行" : "段落"
                onClicked: backend.toggleLineMode()
            }
            TBtn {
                text: "⚙"
                active: root.settingsOpen
                onClicked: root.settingsOpen = !root.settingsOpen
            }
            TBtn {
                text: "独立窗口"
                onClicked: embed.openStandalone()
            }
        }
    }

    Rectangle {
        id: sep1
        anchors.top: toolbar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: "#e6e9ee"
    }

    // ==================== 主体 ====================
    Item {
        id: body
        anchors.top: sep1.bottom
        anchors.bottom: footer.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 8

        // ---------- 原文 ----------
        Rectangle {
            id: srcBox
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: Math.max(92, Math.round(parent.height * 0.36))
            radius: 6
            color: "#ffffff"
            border.width: 1
            border.color: "#e2e7ee"

            Item {
                id: srcHead
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 26

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
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
                    spacing: 4

                    TBtn {
                        text: "从记录刷新"
                        onClicked: embed.reload()
                    }
                    TBtn {
                        text: "复制"
                        onClicked: backend.copySource()
                    }
                    TBtn {
                        text: "清空"
                        onClicked: backend.sourceText = ""
                    }
                }
            }

            Flickable {
                id: srcFlick
                anchors.top: srcHead.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 8
                anchors.rightMargin: 6
                anchors.bottomMargin: 6
                contentWidth: width
                contentHeight: srcEdit.contentHeight + 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: srcEdit
                    width: srcFlick.width
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
                    text: "点「从记录刷新」载入记录页最后一条，也可以直接粘贴文本。"
                    color: "#9aa4af"
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                    width: srcFlick.width
                    wrapMode: Text.Wrap
                }
            }
        }

        // ---------- 译文 ----------
        Rectangle {
            id: dstBox
            anchors.top: srcBox.bottom
            anchors.topMargin: 6
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            radius: 6
            color: "#f7f9fc"
            border.width: 1
            border.color: "#e2e7ee"

            Item {
                id: dstHead
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 26

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 8
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
                    spacing: 4

                    TBtn {
                        text: "复制译文"
                        onClicked: backend.copyTarget()
                    }
                }
            }

            Flickable {
                id: dstFlick
                anchors.top: dstHead.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: 8
                anchors.rightMargin: 6
                anchors.bottomMargin: 6
                contentWidth: width
                contentHeight: dstEdit.contentHeight + 4
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: dstEdit
                    width: dstFlick.width
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
                    text: backend.busy ? "正在翻译…" : "点「从记录刷新」载入记录页最后一条，点「翻译」翻译原文框里的内容。"
                    color: "#9aa4af"
                    font.pixelSize: 11
                    font.family: "Microsoft YaHei"
                    width: dstFlick.width
                    wrapMode: Text.Wrap
                }
            }
        }
    }

    // ==================== 底栏 ====================
    Item {
        id: footer
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 34

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: "#e6e9ee"
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.right: actions.left
            anchors.rightMargin: 8
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
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            TBtn {
                text: backend.autoTranslate ? "自动翻译：开" : "自动翻译：关"
                active: backend.autoTranslate
                onClicked: backend.toggleAutoTranslate()
            }
            TBtn {
                text: backend.busy ? "翻译中…" : "翻译"
                primary: true
                enabled: !backend.busy
                onClicked: backend.requestTranslate()
            }
        }
    }

    // ==================== 设置浮层 ====================
    Rectangle {
        id: settings
        visible: root.settingsOpen
        anchors.top: sep1.bottom
        anchors.right: parent.right
        anchors.topMargin: 6
        anchors.rightMargin: 8
        width: Math.min(300, root.width - 16)
        height: settingsCol.height + 20
        radius: 8
        color: "#ffffff"
        border.width: 1
        border.color: "#d6dce5"
        z: 200

        Column {
            id: settingsCol
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 10
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 7

            Text {
                text: "独立窗口热键"
                color: "#1f2328"
                font.pixelSize: 12
                font.bold: true
                font.family: "Microsoft YaHei"
            }

            Row {
                spacing: 6

                TBtn {
                    text: backend.hotkeyEnabled ? "热键：开" : "热键：关"
                    active: backend.hotkeyEnabled
                    onClicked: backend.setHotkeyEnabled(!backend.hotkeyEnabled)
                }

                Rectangle {
                    width: 118
                    height: 28
                    radius: 6
                    color: "#f7f9fc"
                    border.width: 1
                    border.color: "#d6dce5"

                    TextInput {
                        id: hkInput
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        verticalAlignment: TextInput.AlignVCenter
                        text: backend.hotkeyText
                        selectByMouse: true
                        color: "#1f2328"
                        font.pixelSize: 12
                        font.family: "Consolas"
                        onEditingFinished: backend.applyHotkey(text)
                    }
                }

                TBtn {
                    text: "应用"
                    primary: true
                    onClicked: backend.applyHotkey(hkInput.text)
                }
            }

            Text {
                width: parent.width
                text: "例：ctrl+alt+t、ctrl+shift+f2。按热键会在独立窗口里翻译记录页最后一条。"
                color: "#8c959f"
                font.pixelSize: 10
                wrapMode: Text.Wrap
                font.family: "Microsoft YaHei"
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#eef1f5"
            }

            Text {
                width: parent.width
                text: "翻译服务：" + backend.serviceText
                color: "#57606a"
                font.pixelSize: 11
                wrapMode: Text.Wrap
                font.family: "Microsoft YaHei"
            }

            Row {
                spacing: 4

                TBtn {
                    text: "刷新"
                    onClicked: backend.refreshService()
                }
                TBtn {
                    text: "重启服务"
                    onClicked: backend.restartService()
                }
                TBtn {
                    text: "日志目录"
                    onClicked: backend.openLogs()
                }
            }
        }
    }
}
