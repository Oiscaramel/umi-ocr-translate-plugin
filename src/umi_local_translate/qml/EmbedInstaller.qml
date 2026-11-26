import QtQuick 2.15

// 把「翻译」标签和翻译页交给 Umi 自己的 Container 控制器：
//   TabBar.addItem()    -> 第三个标签（选中态/互斥高亮由 TabBar 管）
//   SwipeView.addItem() -> 第三个页面（切换动画原生）
Item {
    visible: false

    Component.onCompleted: {
        if (___tab)
            anchorBar.addItem(___tab)
        if (___page)
            anchorArea.addItem(___page)
    }
}
