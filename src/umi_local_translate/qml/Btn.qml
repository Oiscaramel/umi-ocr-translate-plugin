import QtQuick 2.15

Rectangle {
    id: btn

    property string text: ""
    property bool primary: false
    property bool active: false
    property bool enabled: true

    signal clicked()

    implicitWidth: label.implicitWidth + 20
    implicitHeight: 28
    radius: 7
    opacity: btn.enabled ? 1.0 : 0.5

    color: {
        if (btn.active) return "#1f6feb"
        if (btn.primary) return mouse.containsMouse ? "#2f86f6" : "#1f6feb"
        return mouse.containsMouse ? "#e7eef8" : "#f2f4f7"
    }
    border.width: 1
    border.color: btn.active || btn.primary ? "#1f6feb" : "#d6dce5"

    Text {
        id: label
        anchors.centerIn: parent
        text: btn.text
        color: (btn.active || btn.primary) ? "#ffffff" : "#24292f"
        font.pixelSize: 12
        font.family: "Microsoft YaHei"
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (btn.enabled) btn.clicked()
    }
}
