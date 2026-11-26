import QtQuick 2.15
import QtQuick.Controls 2.15

// 真正的第三个标签：把自己 addItem 进 Umi 的 TabBar。
// 这样选中态、互斥高亮、样式都由 TabBar 自己维护，不存在"两个同时高亮"。
TabButton {
    id: root

    readonly property var th: hostWindow ? hostWindow.theme : null
    readonly property var sz: hostWindow ? hostWindow.size_ : null
    readonly property string title: "翻译"

    text: ""
    padding: 0
    height: anchorBar ? anchorBar.height : 30
    width: labelText.implicitWidth + (sz ? sz.line * 2 : 32)

    contentItem: Text {
        id: labelText
        text: root.title
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        color: root.checked
               ? (root.th ? root.th.textColor : "#1f2328")
               : (root.th ? root.th.subTextColor : "#57606a")
        font.pixelSize: root.sz ? root.sz.text : 14
        font.family: root.th ? root.th.fontFamily : "Microsoft YaHei"
        font.bold: root.checked
    }

    // 和 TabPanel.qml 里原生标签完全一样的配色
    background: Item {
        Rectangle {
            anchors.fill: parent
            color: root.checked
                   ? (root.th ? root.th.coverColor3 : "#33000000")
                   : (root.th ? root.th.coverColor2 : "#22000000")
        }
        Rectangle {
            anchors.fill: parent
            visible: root.hovered
            color: root.th ? root.th.coverColor1 : "#11000000"
        }
    }

    onClicked: {
        // 选中动作由 TabBar 处理，这里不需要额外逻辑
    }

    Component.onCompleted: {
        if (anchorBar)
            anchorBar.addItem(root)
    }
}
