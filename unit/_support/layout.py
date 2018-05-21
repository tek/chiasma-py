from chiasma.data.view_tree import ViewTree, map_panes
from chiasma.ui.simple import SimpleLayout, SimplePane

from amino import List
from amino.func import const
from amino.lenses.lens import lens
from amino.boolean import true

three = ViewTree.layout(
    SimpleLayout.cons('main', vertical=False),
    List(
        ViewTree.pane(SimplePane.cons('one')),
        ViewTree.layout(
            SimpleLayout.cons('sub', vertical=True),
            List(
                ViewTree.pane(SimplePane.cons('two')),
                ViewTree.pane(SimplePane.cons('three')),
            )
        ),
    )
)
two_vertical = ViewTree.layout(
    SimpleLayout.cons('root', vertical=False),
    List(
        ViewTree.layout(
            SimpleLayout.cons('left', vertical=True),
            List(
                ViewTree.pane(SimplePane.cons('one', open=True)),
            ),
        ),
        ViewTree.layout(
            SimpleLayout.cons('right', vertical=True),
            List(
                ViewTree.pane(SimplePane.cons('two')),
            ),
        )
    )
)
open_all_panes = map_panes(const(True), lens.open.set(true))

__all__ = ('two_vertical', 'open_all_panes', 'three',)
