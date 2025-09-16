#!/usr/bin/env python3
import math
import os
import sys
from typing import MutableMapping, Self
import argparse
import dataclasses
from typing import Any, Iterable, Mapping, Type
from PySide6 import QtWidgets, QtGui, QtCore
from PIL import Image, ImageQt
import subprocess
import json


def get_sway_outputs() -> list[Mapping[str, Any]]:
    return json.loads(subprocess.getoutput("swaymsg -t get_outputs -r"))


@dataclasses.dataclass
class Monitor:
    name: str
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_sway(cls: Type[Self], config: Mapping[str, Any]) -> Self:
        rect = config["rect"]
        return cls(
            config["name"],
            rect["x"],
            rect["y"],
            rect["width"],
            rect["height"],
        )

    def cut(self, img: Image.Image, x: int, y: int) -> Image.Image:
        x = int(self.x + x)
        y = int(self.y + y)
        crop = (x, y, x + self.width, y + self.height)
        img.crop(crop)

@dataclasses.dataclass
class Desktop:
    monitors: list[Monitor]

    @classmethod
    def from_sway(
        cls: Type[Self],
        config: Iterable[Mapping[str, Any]],
    ) -> Self:
        return cls([Monitor.from_sway(c) for c in config])

    @property
    def width(self) -> int:
        return max(m.x + m.width for m in self.monitors)

    @property
    def height(self) -> int:
        return max(m.y + m.height for m in self.monitors)

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


class Wallpaper(QtWidgets.QLabel):
    def __init__(
        self,
        img: QtGui.QImage,
        desktop: Desktop,
        results: MutableMapping[str, Any],
        display_scale: float = 0.2,
    ):
        super().__init__()
        self.img = img
        self.desktop = desktop
        self.results = results
        self.display_scale = display_scale
        self.original_width = img.width()
        self.original_height = img.height()
        self.aspect_ratio = img.width() / img.height()
        self.wp_scale = 1
        self.starting_loc: tuple[float, float] | None = None
        self.update_pixmap()
        self.wpx = 0
        self.wpy = 0

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        point = QtCore.QPoint(
            int(self.wpx * self.display_scale),
            int(self.wpy * self.display_scale),
        )
        pen = QtGui.QPen(QtGui.QColor.fromRgb(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPixmap(point, self.pixmap())
        for monitor in self.desktop.monitors:
            rect = QtCore.QRect(
                int(monitor.x * self.display_scale),
                int(monitor.y * self.display_scale),
                int(monitor.width * self.display_scale),
                int(monitor.height * self.display_scale),
            )
            painter.drawRect(rect)
        painter.end()

    def wheelEvent(self, event: QtGui.QWheelEvent, /) -> None:
        direction = event.angleDelta().y()
        if direction > 0:
            self.wp_scale += 0.05
        if direction < 0:
            self.wp_scale -= 0.05
        self.update_pixmap()
        return None

    def mousePressEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.starting_loc = (
                event.position().x() / self.display_scale,
                event.position().y() / self.display_scale,
            )

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.button == QtCore.Qt.MouseButton.LeftButton:
            self.starting_loc = None

    def mouseMoveEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return
        if self.starting_loc is None:
            raise RuntimeError("Did not determine mouse pointer position")
        ox, oy = self.starting_loc
        cx = event.position().x() / self.display_scale
        cy = event.position().y() / self.display_scale
        self.starting_loc = (cx, cy)
        self.wpx += cx - ox
        self.wpy += cy - oy
        self.update()

    def update_pixmap(self) -> None:
        sz = QtCore.QSize()
        sz.setWidth(
            int(self.original_width * self.display_scale * self.wp_scale)
        )
        sz.setHeight(
            int(self.original_height * self.display_scale * self.wp_scale)
        )
        self.setPixmap(QtGui.QPixmap.fromImage(self.img).scaled(sz))

    def keyPressEvent(self, event: QtGui.QKeyEvent, /) -> None:
        if event.key() != QtCore.Qt.Key.Key_Space:
            return
        width = math.ceil(self.original_width * self.wp_scale)
        height = math.ceil(self.original_height * self.wp_scale)
        self.results["size"] = (width, height)
        self.results["xoff"] = -self.wpx
        self.results["yoff"] = -self.wpy
        self.close()


def main(args: argparse.Namespace):
    app = QtWidgets.QApplication()
    img = Image.open(args.filepath)
    desktop = Desktop.from_sway(get_sway_outputs())
    results = {}
    wp = Wallpaper(ImageQt.ImageQt(img), desktop, results, args.scale)
    wp.show()
    app.exec()
    scaled = img.resize(results["size"])
    for monitor in desktop.monitors:
        cut = monitor.cut(scaled, results["xoff"], results["yoff"])
        cut.save(os.path.join(args.output_dir, f"{monitor.name}.png"))


if __name__ == "__main__":
    args = argparse.ArgumentParser("Sway Wallpaper Splitter")
    args.add_argument("filepath", type=str)
    args.add_argument("output_dir", type=str)
    args.add_argument(
        "--scale",
        type=float,
        default=0.2,
        help="The multiplier of the desktop relative to the real size.",
    )
    main(args.parse_args())
