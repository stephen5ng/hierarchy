import argparse
import time
import sys
import os

import platform
if platform.system() != "Darwin":
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
else:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions


class SampleBase(object):
    def process(self) -> None:
        options = RGBMatrixOptions()

        options.hardware_mapping = "regular"
        options.row_address_type = 0
        options.multiplexing = 0
        options.pwm_bits = 11
        options.brightness = 100
        options.pwm_lsb_nanoseconds = 130
        options.led_rgb_sequence = "RGB"
        options.panel_type = ""

        options.gpio_slowdown = 4
        options.disable_hardware_pulsing = True
        options.drop_privileges = True

        if platform.system() == "Darwin":
            options.rows = 256
            options.cols = 192
            options.chain_length = 1
            options.parallel = 1
        else:
            options.rows = 32
            options.cols = 64
            options.chain_length = 8
            options.parallel = 3


        options.gpio_slowdown = 5
        options.multiplexing = 1
        options.pixel_mapper_config = "U-mapper"
        options.brightness = 100
        #sudo examples-api-use/demo -D0 --led-no-hardware-pulse --led-cols=64 --led-rows=32 --led-slowdown-gpio=5 --led-multiplexing=1 --led-pixel-mapper=U-mapper --led-chain 8 --led-parallel=3 

        self.matrix = RGBMatrix(options = options)

