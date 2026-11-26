import QtQuick 2.15

// 内嵌面板用的按钮：对齐 Umi 原生 Button_ 的外观
//   默认透明 -> 悬停 coverColor2 -> 按下 coverColor4
//   选中 active -> coverColor3 + 加粗；primary -> 蓝色实心
Rectangle {
    id: btn

    readonly property var th: hostWindow ? hostWindow.theme : null
    readonly property var sz: hostWindow ? hostWindow.size_ : null

    property string text: ""
    property bool primary: false
    property bool active: false
    property bool enabled: true
    signal clicked()

    implicitWidth: label.implicitWidth + (sz ? sz.line : 16)
    implicitHeight: sz ? Math.round(sz.line * 1.5) : 24
    radius: sz ? sz.btnRadius : 4
    opacity: enabled ? 1.0 : 0.45

    color: {
        if (primary)
            return mouse.containsMouse ? "#2f86f6" : "#1f6feb"
        if (active)
            return th ? th.coverColor3 : "#33000000"
        if (mouse.pressed)
            return th ? th.coverColor4 : "#55000000"
        if (mouse.containsMouse)
            return th ? th.coverColor2 : "#22000000"
        return "#00000000"
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: btn.text
        color: btn.primary ? "#ffffff" : (btn.th ? btn.th.textColor : "#1f2328")
        font.pixelSize: btn.sz ? btn.sz.text : 13
        font.family: btn.th ? btn.th.fontFamily : "Microsoft YaHei"
        font.bold: btn.active || btn.primary
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (btn.enabled) btn.clicked()
    }
}
