import math
import platform
import subprocess
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
import pyautogui


CAMERA_INDEX = 0
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
SMOOTHING_ALPHA = 0.28
CLICK_DISTANCE_THRESHOLD = 0.035
VOLUME_DEBOUNCE_SECONDS = 0.12

pyautogui.FAILSAFE = False


@dataclass
class SmoothPoint:
    x: float = 0.0
    y: float = 0.0
    initialized: bool = False

    def update(self, nx: float, ny: float, alpha: float):
        if not self.initialized:
            self.x, self.y = nx, ny
            self.initialized = True
            return self.x, self.y
        self.x = alpha * nx + (1.0 - alpha) * self.x
        self.y = alpha * ny + (1.0 - alpha) * self.y
        return self.x, self.y


def set_system_volume(percent: int):
    percent = max(0, min(100, int(percent)))
    sys_name = platform.system().lower()

    if "windows" in sys_name:
        try:
            from ctypes import POINTER, cast

            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            min_v, max_v, _ = volume.GetVolumeRange()
            target_db = min_v + (max_v - min_v) * (percent / 100.0)
            volume.SetMasterVolumeLevel(target_db, None)
            return
        except Exception:
            return

    if "linux" in sys_name:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], check=False)
        return

    if "darwin" in sys_name:
        subprocess.run(["osascript", "-e", f"set Volume {percent / 12.5}"], check=False)


def distance(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def main():
    screen_w, screen_h = pyautogui.size()
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.65,
        min_tracking_confidence=0.65,
    )
    mp_draw = mp.solutions.drawing_utils

    smooth = SmoothPoint()
    last_click = 0.0
    last_volume_set = 0.0

    prev_time = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if result.multi_hand_landmarks:
            hand = result.multi_hand_landmarks[0]
            lm = hand.landmark

            index_tip = lm[8]
            thumb_tip = lm[4]

            mapped_x = np.interp(index_tip.x, [0.05, 0.95], [0, screen_w])
            mapped_y = np.interp(index_tip.y, [0.05, 0.95], [0, screen_h])

            sx, sy = smooth.update(mapped_x, mapped_y, SMOOTHING_ALPHA)
            pyautogui.moveTo(sx, sy, _pause=False)

            pinch = distance(index_tip, thumb_tip)
            now = time.time()

            if pinch < CLICK_DISTANCE_THRESHOLD and now - last_click > 0.25:
                pyautogui.click()
                last_click = now

            if now - last_volume_set >= VOLUME_DEBOUNCE_SECONDS:
                vol_percent = int(np.interp(pinch, [0.02, 0.25], [0, 100]))
                set_system_volume(vol_percent)
                last_volume_set = now

            mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
            cv2.putText(
                frame,
                f"Pinch:{pinch:.3f}",
                (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (50, 220, 50),
                2,
            )

        now_t = time.time()
        fps = 1.0 / max(1e-6, now_t - prev_time)
        prev_time = now_t

        cv2.putText(
            frame,
            f"FPS: {fps:.1f}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )
        cv2.imshow("Hand Control IA", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
