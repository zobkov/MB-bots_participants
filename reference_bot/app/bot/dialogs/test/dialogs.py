from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Radio, Row, ScrollingGroup, Next, Cancel, Back, Start, Group, Column
from aiogram_dialog.widgets.text import Format, Const

from app.bot.states.test import TestSG

test_dialog = Dialog(
    Window(
        Format("1 - YO bithceS!!"),
        Column(
            Next(Const(">")),
            Start(Const("START"),state=TestSG.test_1, id="go_start_1"),
        ),
        state = TestSG.test_1
    ),
    Window(
        Format("2 - YO DICKHEADS!!"),
        Column(
            Back(Const("<")),
            Start(Const("START"),state=TestSG.test_1, id="go_start_1"),
        ),
        state = TestSG.test_2
    ),
)