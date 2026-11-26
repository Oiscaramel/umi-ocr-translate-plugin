import QtQuick 2.15

// 夹在"右侧面板"和"左侧识图面板"之间的一层底衬，颜色与面板底色一致。
// 作用：切换动画里溢出的页面会被这层挡住，而左侧面板的透明边距处看到的也是同色，
// 视觉上等效于在分栏处裁剪。
Rectangle {
    readonly property var th: hostWindow ? hostWindow.theme : null

    property var target: null

    x: target ? target.x : 0
    y: target ? target.y : 0
    width: target ? target.width : 0
    height: target ? target.height : 0
    color: th ? th.bgColor : "#eeeeee"
}
