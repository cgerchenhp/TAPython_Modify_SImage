import base64
import os.path
import time
import zlib
from PIL import Image
import numpy as np
import cv2
import unreal
from Utilities.Utils import Singleton


def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__ :-<40} took {end_time - start_time:.6f} seconds to run.")
        return result

    return wrapper


class SetImageDataTest(metaclass=Singleton):
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.data: unreal.ChameleonData = unreal.PythonBPLib.get_chameleon_data(self.json_path)
        self.ui_image_name = "SImage_A"

        image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "img", "test_2048.png"))
        if not os.path.exists(image_path):
            unreal.log_warning(f"image_path: {image_path} not exists")

        tapython_version = unreal.PythonBPLib.get_ta_python_version()
        if tapython_version["Major"] <= 1:
            if tapython_version["Minor"] < 2 or (tapython_version["Minor"] == 2 and tapython_version["Patch"] < 1):
                current_version = f'{tapython_version["Major"]}.{tapython_version["Minor"]}.{tapython_version["Patch"]}'
                unreal.PythonBPLib.confirm_dialog(
                    f"This feature is only available in TaPython 1.2.1 or later. current: {current_version}"
                    , dialog_title="Warning")

        self.im_rgb = np.asarray(Image.open(image_path))  # Image will return a rgb order numpy array
        self.im = cv2.imread(image_path)  # cv2.imread will return a bgr order numpy array

        # we will use im.ctype.data to get the memory address of the numpy array
        # , so we need to make sure the numpy array is contiguous
        # in this case, below code is not nessary, but if you modify the im
        # , for instance transpose the im, you need to make sure the im is contiguous
        self.im = np.ascontiguousarray(self.im, dtype=np.uint8)

        self.w, self.h = self.im.shape[1], self.im.shape[0]

        self.channel = self.im.shape[2] if len(self.im.shape) > 2 else 1
        self.im_bytes = self.im.tobytes()
        self.im_base64_str = self.encodeb64()
        self.video_path = os.path.abspath(os.path.join(unreal.Paths.engine_dir()
                                                  , "../Templates/TP_ME_VProdBP/Content/Movies/MediaExample.mp4"))
        unreal.Paths.get_engine_localization_paths()
        self.cap = None

    @timeit
    def encodeb64(self):
        return base64.b64encode(self.im_bytes).decode('ascii')

    @timeit
    def on_clear_click(self):
        self.data.set_image_data(self.ui_image_name, b'\xff', 1, 1, 1)

    @timeit
    def set_image_with_uint8(self):
        self.data.set_image_data(self.ui_image_name, self.im_bytes, self.w, self.h, self.channel, True)

    @timeit
    def set_image_with_uint8_compressed(self):
        compressor = zlib.compressobj(level=1)  # use fast compression or use zlib.compress()
        compressed_data = compressor.compress(self.im_bytes) + compressor.flush()
        print(f"compression ratio: {len(compressed_data) / len(self.im_bytes) * 100:.2f}%")
        self.data.set_image_data(self.ui_image_name, compressed_data, self.w, self.h, self.channel, True)

    @timeit
    def set_image_with_base64(self):
        self.data.set_image_data_base64(self.ui_image_name, self.im_base64_str, self.w, self.h, self.channel, True)

    @timeit
    def set_image_with_compress_then_base64(self):
        compressor = zlib.compressobj(level=1)
        compressed_data = compressor.compress(self.im_bytes) + compressor.flush()
        compressed_b64 = base64.b64encode(compressed_data).decode('ascii')
        self.data.set_image_data_base64(self.ui_image_name, compressed_b64, self.w, self.h, self.channel, True)

    def on_tick(self):
        # the max fps is 60
        # set "LogOnTickWarnings=False" in config.ini, if you see the warnings
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.data.set_image_data_from_memory(self.ui_image_name, frame.ctypes.data
                                                     , frame.shape[0] * frame.shape[1] * frame.shape[2]
                                                     , frame.shape[1], frame.shape[0], 3, True)
            else:
                self.cap = None

    def on_play_video(self):
        if not self.cap:
            if os.path.exists(self.video_path):
                self.cap = cv2.VideoCapture(self.video_path)
            else:
                unreal.log_warning(f"video_path: {self.video_path} not exists")

    def on_stop_click(self):
        if self.cap:
            self.cap.release()

    @timeit
    def on_memory_click(self):
        im = self.im
        # im = np.ascontiguousarray(im, dtype=np.uint8)
        size = self.w * self.h * self.channel
        self.data.set_image_data_from_memory(self.ui_image_name, im.ctypes.data, size, self.w, self.h, self.channel,True)
