#!/usr/bin/env python3
import argparse
import dataclasses
import enum
import json
import math
import os
import subprocess
from typing import MutableMapping, Self
from typing import Any, Iterable, Mapping, Type
from PySide6 import QtWidgets, QtGui, QtCore
from PIL import Image, ImageQt

WHITE = QtGui.QColor.fromRgb(255, 255, 255)
RED = QtGui.QColor.fromRgb(255, 0, 0)
ORANGE = QtGui.QColor.fromRgb(255, 150, 0)

_DESCRIPTION = """Scale and cut images to use as wallpapers in sway.
Scale the image with the scroll wheel and move it around with drag and drop.
Then confirm your selection with the space bar.
Your monitor setup will be overlaid.
If the image is zoomed in more than the original resolution the monitor setup
will be orange.
If the image doesn't cover all screens fully the monitor setup will be red.
The program will print the command to set the wallpaper for swaybg and swaylock.
"""


def get_sway_outputs() -> list[Mapping[str, Any]]:
    return json.loads(subprocess.getoutput("swaymsg -t get_outputs -r"))


class ScaleMode(enum.Enum):
    ORIGINAL = 1
    WIDTH = 2
    HEIGHT = 3
    FREE = 4


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
        return img.crop(crop)


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
        self.last_loc: tuple[float, float] | None = None
        self.update_pixmap()
        self.wpx = 0
        self.wpy = 0
        self.wp_mode = ScaleMode.ORIGINAL

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        painter = QtGui.QPainter(self)
        point = QtCore.QPoint(
            int(self.wpx * self.display_scale),
            int(self.wpy * self.display_scale),
        )
        if (
            self.wpx > 0
            or self.wpy > 0
            or self.wpx + self.original_width * self.wp_scale
            < self.desktop.width
            or self.wpy + self.original_height * self.wp_scale
            < self.desktop.height
        ):
            pen = QtGui.QPen(RED)
        elif self.wp_scale > 1:
            pen = QtGui.QPen(ORANGE)
        else:
            pen = QtGui.QPen(WHITE)
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
        self.wp_mode = ScaleMode.FREE
        return None

    def mousePressEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.starting_loc = (
                event.position().x() / self.display_scale,
                event.position().y() / self.display_scale,
            )
            self.last_loc = self.starting_loc
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            print(self.wp_mode)
            if self.wp_mode == ScaleMode.ORIGINAL:
                self.wp_mode = ScaleMode.WIDTH
                self.wp_scale = self.desktop.width / self.original_width
            elif self.wp_mode == ScaleMode.WIDTH:
                self.wp_mode = ScaleMode.HEIGHT
                self.wp_scale = self.desktop.height / self.original_height
            else:
                self.wp_mode = ScaleMode.ORIGINAL
                self.wp_scale = 1
            self.update_pixmap()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.button == QtCore.Qt.MouseButton.LeftButton:
            self.starting_loc = None
            self.last_loc = None

    def mouseMoveEvent(self, event: QtGui.QMouseEvent, /) -> None:
        if event.buttons() != QtCore.Qt.MouseButton.LeftButton:
            return
        if self.starting_loc is None or self.last_loc is None:
            raise RuntimeError("Did not determine mouse pointer position")
        lx, ly = self.last_loc
        ox, oy = self.starting_loc
        cx = event.position().x() / self.display_scale
        cy = event.position().y() / self.display_scale
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
            dx = abs(cx - ox)
            dy = abs(cy - oy)
            if dx > dy:
                self.wpx += cx - lx
            else:
                self.wpy += cy - ly
        else:
            self.wpx += cx - lx
            self.wpy += cy - ly
        self.last_loc = (cx, cy)
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
    if "size" not in results:
        exit(1)
    scaled = img.resize(results["size"])
    swaybg_cmd = ["swaybg"]
    swaylock_cmd = ["swaylock"]
    for monitor in desktop.monitors:
        cut = monitor.cut(scaled, results["xoff"], results["yoff"])
        filepath = os.path.join(args.output_dir, f"{monitor.name}.png")
        cut.save(filepath)
        swaybg_cmd.extend([f"-o {monitor.name} -i {filepath}"])
        swaylock_cmd.extend([f"-i {monitor.name}:{filepath}"])
    print(" ".join(swaybg_cmd))
    print(" ".join(swaylock_cmd))


if __name__ == "__main__":
    args = argparse.ArgumentParser(
        "Sway Wallpaper Splitter",
        usage="./sway-wallpaper-splitter.py my-wp.jpg .",
        description=_DESCRIPTION,
    )
    args.add_argument(
        "filepath", type=str, help="The filepath to the wallpaper"
    )
    args.add_argument(
        "output_dir", type=str, help="The directory where to store the images"
    )
    args.add_argument(
        "--scale",
        type=float,
        default=0.2,
        help="The multiplier of the desktop relative to the real size (default=0.2).",
    )
    main(args.parse_args())
