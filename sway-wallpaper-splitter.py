#!/usr/bin/env python3
import os
import sys
from typing import Iterable, Self
import argparse
from collections.abc import Mapping
import dataclasses
from typing import Any, Type
from PIL import Image
import subprocess
import json
import tkinter
from tkinter import ttk


def get_sway_outputs() -> list[Mapping[str, Any]]:
    return json.loads(subprocess.getoutput("swaymsg -t get_outputs -r"))


@dataclasses.dataclass
class Monitor:
    name: str
    x: int
    y: int
    width: int
    height: int
    wallpaper = Image.Image | None

    @classmethod
    def from_sway(cls: Type[Self], config: Mapping[str, Any]) -> Self:
        rect = config["rect"]
        return cls(config["name"], rect["x"], rect["y"], rect["width"], rect["height"])

    def clip_wallpaper(self, img: Image.Image) -> Image.Image:
        return img.crop((self.x, self.y, self.x + self.width, self.y + self.height))


@dataclasses.dataclass
class Desktop:
    monitors: list[Monitor]

    @classmethod
    def from_sway(cls: Type[Self], config: Iterable[Mapping[str, Any]]) -> Self:
        return cls([Monitor.from_sway(c) for c in config])

    @property
    def width(self) -> int:
        return max(m.x + m.width for m in self.monitors)

    @property
    def height(self) -> int:
        return max(m.y + m.height for m in self.monitors)

    def add_wallpaper(self, img: Image.Image) -> None:
        width_ratio = img.width / self.width
        height_ratio = img.height / self.height
        if width_ratio < 1 or height_ratio < 1:
            print(
                f"At least one of width ({img.width}) and height ({img.height})"
                " is less than the size of the desktop "
                f"(width: {self.width}, height: {self.height})",
                file=sys.stderr,
            )
        if width_ratio < height_ratio:
            new_width = self.width
            new_height = int(img.height * new_width / img.width)
        else:
            new_height = self.height
            new_width = int(img.width * new_height / img.height)
        print(new_width, new_height)
        scaled = img.resize((new_width, new_height)).crop(
            (0, 0, self.width, self.height)
        )
        self.wallpaper = scaled

    def cut(self) -> dict[str, Image.Image]:
        return {m.name: m.clip_wallpaper(self.wallpaper) for m in self.monitors}


def main(args: argparse.Namespace):
    desktop = Desktop.from_sway(get_sway_outputs())
    img = Image.open(args.filepath)
    # desktop.add_wallpaper(img)
    # for monitor, img in desktop.cut().items():
    #     img.save(os.path.join(args.output_dir, monitor + ".png"))
    # root = tkinter.Tk()
    # frm = ttk.Frame(roow, padding=10)

    # print(img)
    # img.show()


if __name__ == "__main__":
    args = argparse.ArgumentParser("Sway Wallpaper Splitter")
    args.add_argument("filepath", type=str)
    args.add_argument("output_dir", type=str)
    main(args.parse_args())
